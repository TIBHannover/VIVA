import multiprocessing

import redis
from flask import abort

from common.SharedUtils import create_postgres_connection, sse_send_training_data, set_training_stop
from common.SharedValues import SharedValues
from common.consts import *
from flask_app.control import input_validation_train_infer, redis_reset_startup

training_start_lock: multiprocessing.Lock = multiprocessing.Lock()


def start_training(redis_pool: redis.ConnectionPool, sv_instance: SharedValues):
    redis_con = redis.Redis(connection_pool=redis_pool)
    # input validation
    gpu_selection, batch_size = input_validation_train_infer(redis_con, sv_instance.compatible_gpus)

    # check run conditions
    postgres_con = create_postgres_connection()
    postgres_cur = postgres_con.cursor()
    postgres_cur.execute(
        """SELECT count(*)
        FROM imageannotation
        JOIN class c on c.id = imageannotation.classid
        WHERE classtypeid = %s
        GROUP BY classid
        HAVING count(*) > %s
        LIMIT 1""",
        (CLASS_TYPE_CONCEPT, int(os.environ["TRAIN_MIN_ANNO_PER_CLASS"])))
    prerequisite = postgres_cur.fetchone()
    postgres_cur.close()
    postgres_con.close()
    if not prerequisite:
        redis_con.close()
        abort(400, f"Not enough data with {os.environ['TRAIN_MIN_ANNO_PER_CLASS']} as minimum number of positive "
                   "samples per concept")

    with training_start_lock:
        redis_reset_startup(redis_con, "Training",
                            os.environ['REDIS_KEY_TRAINING_RUN'],
                            os.environ['REDIS_KEY_TRAINING_TIME'],
                            os.environ['REDIS_KEY_TRAINING_TIME_ETE'],
                            os.environ['REDIS_KEY_TRAINING_EXCEPTION'],
                            os.environ['REDIS_KEY_TRAINING_CURRENT'],
                            os.environ['REDIS_KEY_TRAINING_TOTAL'])
        redis_con.delete(os.environ['REDIS_KEY_TRAINING_GPUS'])
        [redis_con.lpush(os.environ['REDIS_KEY_TRAINING_GPUS'], gpu_idx) for gpu_idx in reversed(gpu_selection)]
        redis_con.set(os.environ['REDIS_KEY_TRAINING_BATCH_SIZE'], batch_size)
        redis_con.delete(os.environ['REDIS_KEY_TRAINING_MAP'])
        redis_con.delete(os.environ['REDIS_KEY_TRAINING_LOSS'])
        redis_con.delete(os.environ['REDIS_KEY_TRAINING_LR'])

        # set event in shared memory for export start
        sv_instance.training.start.set()

    sse_send_training_data(sv_instance, redis_con)
    redis_con.close()


def stop_training(redis_pool: redis.ConnectionPool, sv_instance: SharedValues):
    # check if training is running - then stop it - otherwise check to reset
    redis_con = redis.Redis(connection_pool=redis_pool)
    if int(redis_con.get(os.environ['REDIS_KEY_TRAINING_RUN']) or 0) == 1:
        sv_instance.training.stop.set()
        set_training_stop(redis_con, sv_instance, exception="User canceled training run")
    redis_con.close()
