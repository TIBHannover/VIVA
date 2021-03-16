import os
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout

from common.FileSSELogger import FileSSELogger
from common.SharedUtils import create_redis_connection, set_training_stop
from common.SharedValues import SharedValues
from common.consts import DOCKER_ATTACH_LOGS, get_datetime_str, FILE_NAME_LOG_TRAINING
from .VIVATraining import train_viva_net


def start_train(sv_instance: SharedValues):
    # create options dictionary
    redis_con = create_redis_connection()
    start_time = int(redis_con.get(os.environ['REDIS_KEY_TRAINING_TIME']))
    options = {
        'batch_size': int(redis_con.get(os.environ['REDIS_KEY_TRAINING_BATCH_SIZE'])),
        'start_time': start_time
    }
    redis_con.close()

    file_sse_logger = FileSSELogger(FILE_NAME_LOG_TRAINING, sv_instance.flask_app, os.environ['FLASK_SSE_TRAINING_LOG'])

    print("CUDA_VISIBLE_DEVICES =", os.environ["CUDA_VISIBLE_DEVICES"])

    with redirect_stdout(file_sse_logger):
        with redirect_stderr(file_sse_logger):
            try:
                train_viva_net(options, sv_instance)
                file_sse_logger.copy_to(os.path.join(DOCKER_ATTACH_LOGS, get_datetime_str(start_time),
                                                     FILE_NAME_LOG_TRAINING))
                train_exception = None
            except Exception as e:
                train_exception = str(e)
                print(repr(e), file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
            except KeyboardInterrupt:
                return

    # set training to stopped
    redis_con = create_redis_connection()
    set_training_stop(redis_con, sv_instance, exception=train_exception)
    redis_con.close()
