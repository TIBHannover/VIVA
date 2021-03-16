import csv
import os
import shutil
from datetime import datetime
from typing import List, Dict, Tuple, Union

import psycopg2.extensions
import redis

from common.SharedUtils import create_redis_connection, sse_send_export_data, SharedValues


def get_videos(db_cursor: psycopg2.extensions.cursor) -> List[Tuple[int, str]]:
    db_cursor.execute("""
        SELECT id, path 
        FROM video
        ORDER BY id ASC; """)

    return db_cursor.fetchall()


def get_keyframes(db_cursor: psycopg2.extensions.cursor, video_id: int) -> List[Tuple[int]]:
    db_cursor.execute("""
        SELECT number 
        FROM videoframe
        WHERE videoid = %s
        ORDER BY number ASC; """, (video_id,))

    return db_cursor.fetchall()


def get_video_predictions(db_cursor: psycopg2.extensions.cursor, video_id: int, class_type_id: int, model_id: int,
                          threshold: int) -> List[Tuple[str, int, float, str]]:
    db_cursor.execute("""
        SELECT 
            class.name AS classname, 
            videoframe.number AS keyframe, 
            imageprediction.score AS score
        FROM videoframe
        JOIN image ON videoframe.imageid = image.id
        JOIN imageprediction ON imageprediction.imageid = image.id
        JOIN class ON imageprediction.classid = class.id
        WHERE videoframe.videoid = %s
        AND class.classtypeid = %s
        AND modelid = %s
        AND score >= %s
        ORDER BY classname,keyframe; """, (video_id, class_type_id, model_id, threshold / 100))

    return db_cursor.fetchall()


def get_class_type_name(db_cursor: psycopg2.extensions.cursor, class_type_id: int) -> Union[None, Tuple[str]]:
    db_cursor.execute("""
        SELECT name
        FROM classtype
        WHERE id = %s""", (class_type_id,))
    return db_cursor.fetchone()


def group_results(results: List[Tuple[str, int, float, str]],
                  video_name: str,
                  video_keyframes: List[int],
                  allow_single_frame: bool = False,
                  milliseconds_per_frame: float = 1000 / 25,
                  score_round_decimals: int = 4) -> List[Dict[str, str]]:
    res_grouped = []

    curr_item = {}
    curr_keyframe = 0
    keyframe_count = len(video_keyframes)

    for (class_name, keyframe, score) in results:
        keyframe_seconds = int(round(keyframe * milliseconds_per_frame))

        if (curr_item  # and video_name == curr_item['videoname']
                and class_name == curr_item['classname']
                and curr_keyframe + 1 < keyframe_count
                and keyframe == video_keyframes[curr_keyframe + 1]):

            curr_item['duration (ms)'] = keyframe_seconds - curr_item['start (ms)']
            curr_keyframe += 1

            if score > curr_item['score']:
                curr_item['score'] = round(score, score_round_decimals)

        else:
            if curr_item and (curr_item['duration (ms)'] > milliseconds_per_frame or allow_single_frame):
                res_grouped.append(curr_item)

            curr_item = {
                'classname': class_name,
                'videoname': video_name,
                'start (ms)': keyframe_seconds,
                'duration (ms)': int(round(milliseconds_per_frame)),
                'score': round(score, score_round_decimals)
            }
            curr_keyframe = video_keyframes.index(keyframe)

    return res_grouped


def write_csv(data: List[Dict[str, str]], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode='w', newline='') as file:
        if data and type(data[0]) == dict:
            writer = csv.DictWriter(file, fieldnames=data[0].keys(), delimiter=',')
            writer.writeheader()
        else:
            writer = csv.writer(file, delimiter=',')
            writer.writerow(['classname', 'videoname', 'start (ms)', 'duration (ms)', 'score'])

        writer.writerows(data)


def update_status_information(app_name: str, redis_con: redis.Redis, sv_instance: SharedValues,
                              videos_cur: int) -> None:
    redis_con.set(os.environ['REDIS_KEY_EXPORT_CURRENT'].format(app_name), videos_cur)
    sse_send_export_data(sv_instance, app_name, redis_con)


def export_concept_detections_to_csv_files(options: Dict[str, Union[str, int, float]], sv_instance: SharedValues,
                                           postgres_cur: psycopg2.extensions.cursor, output_folder: str = 'results',
                                           log: bool = False) -> None:
    # fetch videos
    videos = get_videos(postgres_cur)
    video_count_tot = len(videos)
    video_count_cur = 0

    if log:
        print("  Video-Query returned", video_count_tot, "results")
        print()

    # create output dir
    output = os.path.join(output_folder, options['model_date_str'], str(options['class_type_id']))
    os.makedirs(output, exist_ok=True)

    # create redis connection for client updates
    app_name = options['app_name']
    redis_con = create_redis_connection()
    sse_update_video_count = int(os.environ['EXPORT_SSE_UPDATE_PER_VIDEOS'])
    redis_con.set(os.environ['REDIS_KEY_EXPORT_TOTAL'].format(app_name), video_count_tot)
    redis_con.set(os.environ['REDIS_KEY_EXPORT_TIME_ETE'].format(app_name),
                  int(datetime.timestamp(datetime.now())))
    sse_send_export_data(sv_instance, app_name, redis_con)

    # fetch keyframes and predictions for each video
    for video_id, video_path in videos:
        video_name = os.path.splitext(os.path.basename(video_path))[0]

        # fetch keyframes
        video_keyframes = get_keyframes(postgres_cur, video_id)
        video_keyframes = [v[0] for v in video_keyframes]
        if log:
            print("  Keyframe-Query for video", video_id, "returned", len(video_keyframes), "results")

        # fetch predictions
        results = get_video_predictions(postgres_cur, video_id, options['class_type_id'], options['model_id'],
                                        options['threshold'])
        if log:
            print("  Prediction-Query for video", video_id, "returned", len(results), "results")

        # write grouped results to csv (keeping single frame predictions)
        results_grouped = group_results(results, video_name, video_keyframes, allow_single_frame=True)
        write_csv(results_grouped, os.path.join(output, os.path.dirname(video_path), '{:s}.csv'.format(video_name)))

        video_count_cur += 1
        if video_count_cur % sse_update_video_count == 0:
            update_status_information(app_name, redis_con, sv_instance, video_count_cur)

    update_status_information(app_name, redis_con, sv_instance, video_count_cur)
    redis_con.close()


def zip_csv_files(options: Dict[str, Union[str, int, float]], output_folder_csv: str = 'results_csv',
                  output_folder_zip: str = 'results', log: bool = False) -> None:
    output = os.path.join(options['model_date_str'], str(options['class_type_id']))
    output_path_zip = os.path.join(output_folder_zip, "{:s}_{:s}_{:d}".format(
        os.environ['EXPORT_FILE_PREFIX_CC'] if options['app_name'] == os.environ['DJANGO_APP_NAME_CONCEPT'] else
        os.environ['EXPORT_FILE_PREFIX_FR'],
        options['model_date_str'],
        options['threshold']))
    if os.path.isfile(output_path_zip + ".zip"):
        os.remove(output_path_zip + ".zip")
    shutil.make_archive(output_path_zip, 'zip', os.path.join(output_folder_csv, output))

    if log:
        print("Zip Archive created at '{:s}'".format(os.path.join(output_folder_zip, output)))


def export_class_detections(options: Dict[str, Union[str, int, float]], postgres_cur: psycopg2.extensions.cursor,
                            sv_instance: SharedValues, output_folder_csv: str = 'results_csv',
                            output_folder_zip: str = 'results', log: bool = False):
    export_concept_detections_to_csv_files(options, sv_instance, postgres_cur, output_folder_csv, log)
    zip_csv_files(options, output_folder_csv, output_folder_zip, log)
