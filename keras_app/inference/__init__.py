import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import Tuple

import requests

from common.FileSSELogger import FileSSELogger
from common.SharedUtils import *
from common.SharedValues import SharedValues
from common.consts import *
from .VIVAInference import inference_viva_net


def get_latest_model(cur: psycopg2.extensions.cursor, class_type_id: int) -> Tuple[int, datetime, bool, str]:
    cur.execute(
        """SELECT model.id, date, inference_stored, dir_name 
        FROM model
        JOIN evaluation e on model.id = e.modelid
        JOIN class c on c.id = e.classid
        WHERE classtypeid = %s
        ORDER BY date DESC
        LIMIT 1""", (class_type_id,))
    latest_model = cur.fetchone()
    return latest_model


def start_inference(sv_instance: SharedValues):
    # check if inference already run for latest model
    pgsql_con = create_postgres_connection()
    pgsql_cur = pgsql_con.cursor()
    latest_model = get_latest_model(pgsql_cur, CLASS_TYPE_CONCEPT)
    pgsql_cur.close()
    pgsql_con.close()
    if latest_model is None or latest_model[2]:
        redis_con = create_redis_connection()
        set_inference_stop(redis_con, sv_instance,
                           exception="No model has been trained yet"
                           if latest_model is None else "Inference did already run for this model")
        redis_con.close()
        return
    latest_model_dir_name = latest_model[3]

    # create options dictionary
    redis_con = create_redis_connection()
    gpu_selection = get_redis_number_list(redis_con, os.environ['REDIS_KEY_INFERENCE_GPUS'])
    options = {
        'gpu_selection': gpu_selection,
        'batch_size': int(redis_con.get(os.environ['REDIS_KEY_INFERENCE_BATCH_SIZE']))
    }
    redis_con.close()

    # start TFS serving
    requests.post("http://" + os.environ['SERVICE_TFS_APP'] + ":8000" + os.environ['URL_TFS_START'],
                  json={os.environ['TFS_POST_JSON_GPUS']: gpu_selection})

    file_sse_logger = FileSSELogger(FILE_NAME_LOG_INFERENCE, sv_instance.flask_app,
                                    os.environ['FLASK_SSE_INFERENCE_LOG'])

    with redirect_stdout(file_sse_logger):
        with redirect_stderr(file_sse_logger):
            try:
                # check if server(s) are ready to process requests
                if len(gpu_selection):
                    wait_for_port(8500, os.environ["SERVICE_TFS_APP"], timeout=30)
                for i, _ in enumerate(gpu_selection):
                    wait_for_port(8500 + i, os.environ["SERVICE_TFS_APP"], timeout=30)

                inference_viva_net(options, sv_instance, latest_model)
                file_sse_logger.copy_to(
                    os.path.join(DOCKER_ATTACH_LOGS, latest_model_dir_name, FILE_NAME_LOG_INFERENCE))
                inference_exception = None
            except Exception as e:
                inference_exception = str(e)
                print(repr(e), file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
            except KeyboardInterrupt:
                print("User stop request", file=sys.stderr)
                return

    # set training to stopped
    redis_con = create_redis_connection()
    set_inference_stop(redis_con, sv_instance, exception=inference_exception)
    redis_con.close()

    requests.post("http://" + os.environ["SERVICE_TFS_APP"] + ":8000" + os.environ["URL_TFS_STOP"])
