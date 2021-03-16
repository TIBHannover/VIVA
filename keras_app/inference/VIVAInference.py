import math
import multiprocessing
import threading
import time

import redis
import tensorflow as tf

from common.MediaPreprocess import *
from common.SharedUtils import create_postgres_pool, sse_send_inference_data, create_redis_connection
from common.SharedValues import SharedValues
from common.consts import *
from inference.TFSClient import process_batch_queue


def get_images(db_cursor: psycopg2.extensions.cursor, collection_id: str) -> List[tuple]:
    db_cursor.execute(
        """SELECT i.id, i.path
        FROM image i
        WHERE collectionid=%s
        ORDER BY i.id""",
        (collection_id,)
    )
    return db_cursor.fetchall()


def delete_predictions_of_model(db_cursor: psycopg2.extensions.cursor, model_id: int):
    db_cursor.execute(
        """DELETE FROM imageprediction
        WHERE modelid = %s""",
        (model_id,)
    )


def get_previous_stored_model(db_cursor: psycopg2.extensions.cursor):
    db_cursor.execute(
        """SELECT modelid
        FROM model
        JOIN evaluation e on model.id = e.modelid
        JOIN class c on c.id = e.classid
        WHERE classtypeid = %s
        AND inference_stored = true
        ORDER BY date DESC
        LIMIT 1""",
        (CLASS_TYPE_CONCEPT,)
    )
    return db_cursor.fetchone()


def set_inference_done(db_cursor: psycopg2.extensions.cursor, model_id: int) -> None:
    db_cursor.execute("UPDATE model SET inference_stored = TRUE WHERE id = %s", (model_id,))


def tfs_client_manager(data_ids: list, db_class_ids: list, model_id: int, options: dict, predict_gen: tf.data.Dataset,
                       data_length: int, sv_instance: SharedValues, redis_con: redis.Redis):
    batch_size = options["batch_size"]
    batch_count = data_length
    batch_add_count = 0
    batch_queue = multiprocessing.Queue()  # FIFO queue

    process_count = len(options['gpu_selection'])
    process_count = 1 if process_count == 0 else min(8, process_count)
    process_list = []
    for idx in range(process_count):
        process = multiprocessing.Process(
            target=process_batch_queue,
            args=(batch_queue, batch_size, model_id, data_ids, db_class_ids, idx, sv_instance))
        process_list.append(process)
        process.start()

    sv_instance.inference.num_finished.value = 0
    sv_instance.inference.running.value = 1
    last_finished_step = 0

    redis_con.set(os.environ['REDIS_KEY_INFERENCE_TIME_ETE'], int(datetime.timestamp(datetime.now())))

    while True:
        q_size = batch_queue.qsize()

        # Feed the queue
        if q_size < process_count * 4 and batch_add_count < batch_count:
            if batch_add_count != batch_count and batch_add_count > process_count * 4 \
                    and batch_count > process_count > q_size and batch_count % process_count == 0:
                print("Warning: Batch queue is nearly empty ({:d})."
                      "Reduced performance might be caused by empty batch queue that cannot be filled up that quickly!"
                      .format(q_size))
            batch_queue.put((batch_add_count, next(predict_gen)))
            batch_add_count += 1

        # stop monitoring and manipulation of queue
        if batch_add_count == batch_count:
            sv_instance.inference.running.value = 0  # signal the clients to stop if queue.get returns nothing
            process_alive = [process.is_alive() for process in process_list]
            if not any(process_alive):
                break

        if q_size > process_count:
            time.sleep(0.2)

        # Update database and send clients message if count of finished images reached defined steps
        new_finished_step = math.floor(sv_instance.inference.num_finished.value / (
                max(12, batch_size) * process_count))
        if last_finished_step != new_finished_step:
            redis_con.set(os.environ['REDIS_KEY_INFERENCE_CURRENT'], sv_instance.inference.num_finished.value)
            threading.Thread(target=sse_send_inference_data, args=(sv_instance, redis_con)).start()
            last_finished_step = new_finished_step

    sse_send_inference_data(sv_instance, redis_con)


def parse_image(filename):
    image = tf.io.read_file(filename)
    image = tf.image.decode_jpeg(image, channels=3)
    image = tf.image.convert_image_dtype(image, tf.float32)
    image = tf.image.resize(image, [DEFAULT_TARGET_SIZE[0], DEFAULT_TARGET_SIZE[1]])
    return image


def gen(filenames):
    for filename in filenames:
        yield parse_image(filename)


def inference_viva_net(options: dict, sv_instance: SharedValues, model: Tuple[int, datetime, bool, str]):
    postgres_pool = create_postgres_pool()
    postgres_con = postgres_pool.getconn()
    postgres_cur = postgres_con.cursor()

    print("Loading images ...")

    model_id = model[0]

    data = list(get_images(postgres_cur, DRA_KEYFRAMES_ID))
    data_ids = [item[0] for item in data]
    data = [os.path.join(DOCKER_ATTACH_MEDIA, item[1]) for item in data]

    predict_gen = tf.data.Dataset.from_generator(
        lambda: gen(data),
        output_types=tf.float32,
        output_shapes=[DEFAULT_TARGET_SIZE[0], DEFAULT_TARGET_SIZE[1], 3])

    predict_gen = predict_gen.batch(options['batch_size']).prefetch(tf.data.experimental.AUTOTUNE)
    predict_gen = iter(predict_gen)

    redis_con = create_redis_connection()
    redis_con.set(os.environ['REDIS_KEY_INFERENCE_TOTAL'], len(data))
    redis_con.set(os.environ['REDIS_KEY_INFERENCE_CURRENT'], 0)
    sse_send_inference_data(sv_instance, redis_con)

    # Classes should/could not be deleted otherwise mapping to classes will fail
    with open(os.path.join(FILE_PATH_TFS_MODEL_DIR, CLASS_MAP_FILE_NAME), "r") as f:
        db_class_ids = [int(x.strip()) for x in f.readlines()]

    # delete all previous image predictions for current model
    delete_predictions_of_model(postgres_cur, model_id)
    postgres_con.commit()
    postgres_cur.close()
    postgres_pool.putconn(postgres_con)

    # start internal multiprocessing - start a process for each TFS server to query
    tfs_client_manager(data_ids, db_class_ids, model_id, options, predict_gen, len(data), sv_instance, redis_con)

    redis_con.close()

    postgres_con = postgres_pool.getconn()
    postgres_cur = postgres_con.cursor()
    previous_prediction_model = get_previous_stored_model(postgres_cur)
    set_inference_done(postgres_cur, model_id)
    postgres_con.commit()
    if previous_prediction_model is not None:
        delete_predictions_of_model(postgres_cur, previous_prediction_model)
        postgres_con.commit()
    postgres_cur.close()
    postgres_pool.putconn(postgres_con)

    postgres_pool.closeall()
