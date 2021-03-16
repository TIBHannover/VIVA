import multiprocessing

import redis
from flask import abort

from common.SharedUtils import set_inference_stop, sse_send_inference_data, sse_send_export_data, create_postgres_connection
from common.SharedValues import SharedValues
from common.consts import *
from flask_app.control import input_validation_train_infer, redis_reset_startup

inference_start_lock: multiprocessing.Lock = multiprocessing.Lock()


def check_if_inference_already_stored():
    postgres_con = create_postgres_connection()
    postgres_cur = postgres_con.cursor()
    postgres_cur.execute(
        """SELECT inference_stored
        FROM model
        JOIN evaluation e on model.id = e.modelid
        JOIN class c on c.id = e.classid
        WHERE classtypeid = %s
        ORDER BY date DESC 
        LIMIT 1
        """,
        (CLASS_TYPE_CONCEPT,)
    )
    model_res = postgres_cur.fetchone()
    postgres_cur.close()
    postgres_con.close()
    if model_res and model_res[0]:
        abort(400, "Inference did already run for this model")


def start_inference(redis_pool: redis.ConnectionPool, sv_instance: SharedValues) -> None:
    redis_con = redis.Redis(connection_pool=redis_pool)
    # input validation
    gpu_selection, batch_size = input_validation_train_infer(redis_con, sv_instance.compatible_gpus)

    # check run conditions
    if (redis_con.get(os.environ['REDIS_KEY_EXPORT_RUN'].format(os.environ['DJANGO_APP_NAME_CONCEPT'])) or "0") == "1":
        redis_con.close()
        abort(400, "Export is currently running")
    check_if_inference_already_stored()

    with inference_start_lock:
        redis_reset_startup(redis_con, "Inference",
                            os.environ['REDIS_KEY_INFERENCE_RUN'],
                            os.environ['REDIS_KEY_INFERENCE_TIME'],
                            os.environ['REDIS_KEY_INFERENCE_TIME_ETE'],
                            os.environ['REDIS_KEY_INFERENCE_EXCEPTION'],
                            os.environ['REDIS_KEY_INFERENCE_CURRENT'],
                            os.environ['REDIS_KEY_INFERENCE_TOTAL'])
        redis_con.delete(os.environ['REDIS_KEY_INFERENCE_GPUS'])
        [redis_con.lpush(os.environ['REDIS_KEY_INFERENCE_GPUS'], gpu_idx) for gpu_idx in reversed(gpu_selection)]
        redis_con.set(os.environ['REDIS_KEY_INFERENCE_BATCH_SIZE'], batch_size)

        # set event in shared memory for export start
        sv_instance.inference.start.set()

    sse_send_inference_data(sv_instance, redis_con)
    sse_send_export_data(sv_instance, os.environ['DJANGO_APP_NAME_CONCEPT'], redis_con)
    redis_con.close()


def stop_inference(redis_pool: redis.ConnectionPool, sv_instance: SharedValues) -> None:
    # check if training is running - then stop it - otherwise check to reset
    redis_con = redis.Redis(connection_pool=redis_pool)
    if int(redis_con.get(os.environ['REDIS_KEY_INFERENCE_RUN']) or 0) == 1:
        sv_instance.inference.stop.set()
        set_inference_stop(redis_con, sv_instance, exception="User canceled inference run")
    redis_con.close()
    return
