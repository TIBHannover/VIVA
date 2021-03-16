import redis
from flask import url_for

from common.SharedValues import SharedValues
from common.consts import *
from hw_info import get_gpu_info


def basic_info(redis_pool: redis.ConnectionPool, sv_instance: SharedValues):
    redis_con = redis.Redis(connection_pool=redis_pool)
    info = {
        'gpu_support': GPU_MODE,
        'gpu_devices': get_gpu_info(redis_con, sv_instance.compatible_gpus)[0],
        'defaults': {
            'training': {
                'batch_size': 64
            }
        },
        'sse': {
            'url': url_for('sse.stream'),
            'types': {
                'hw_info': SSE_TYPE_HW_INFO,
                'train_info': SSE_TYPE_TRAIN_INFO,
                'epoch_info': SSE_TYPE_EPOCH_INFO,
                'log_info': os.environ['FLASK_SSE_TRAINING_LOG']
            }
        },
    }
    redis_con.close()
    return info
