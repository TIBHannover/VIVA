from datetime import datetime
from typing import Tuple, List

import flask
import redis
from flask import request, abort

from hw_info import get_gpu_info


def input_validation_train_infer(redis_con: redis.Redis, gpus_compat: List[int]) -> Tuple[List[int], int]:
    """Validates if required parameters (gpu selection and batch size) are set correctly for a request in flask

    :param redis_con: an instance of Redis connection
    :param gpus_compat: list with indices of TensorFlow compatible GPUs
    :return: Tuple with [0] list of selected gpu indices [1] selected batch size
    """
    gpu_infos = get_gpu_info(redis_con, gpus_compat)[0]
    if "batch_size" not in request.form or (len(gpu_infos) > 0 and "gpu_selection[]" not in request.form):
        redis_con.close()
        if "gpu_selection" in request.form:
            abort(400, "Select at least one GPU")
        abort(400, "Missing parameter")

    gpu_selection = [int(x) for x in request.form.getlist('gpu_selection[]')]
    valid, message = check_gpu_selection(gpu_infos, gpu_selection, gpus_compat)
    if not valid:
        redis_con.close()
        abort(400, message)

    batch_size = int(request.form['batch_size'])
    if batch_size < 1 or batch_size > 512:
        redis_con.close()
        abort(400, "Invalid batch size")

    return gpu_selection, batch_size


def check_gpu_selection(gpu_infos: List[dict], gpu_selection: List[int], gpus_compat: List[int]) -> Tuple[bool, str]:
    """Validates a given GPU selection (provided as list with indices)

    :param gpu_infos: a list with GPU information (returned by get_gpu_info)
    :param gpu_selection: the list with selected GPU indices
    :param gpus_compat: list with indices of TensorFlow compatible GPUs
    :return: Tuple with [0] boolean - true if valid [1] if not valid - reason as string
    """
    if len(gpu_selection) > 0:
        gpu_ids = [x['index'] for x in gpu_infos]
        for gpu_id in gpu_selection:
            if gpu_id not in gpu_ids or gpu_id not in gpus_compat:
                return False, "Invalid gpu selection"
    if len(gpu_selection) == 0 and len(gpus_compat) > 0:
        return False, "At least one GPU has to be selected"
    return True, ""


def redis_reset_startup(redis_con: redis.Redis, process_name: str, key_run: str, key_time: str, key_time_ete: str,
                        key_exception: str, key_current: str, key_total: str) -> None:
    """Check if Redis key for running is set and when ok than reset the keys stored in redis database

    :param redis_con: an instance of Redis connection
    :param process_name: the name of the action that will be started or not
    :param key_run: Redis key for run indication
    :param key_time: Redis key to store time information (start time or runtime)
    :param key_time_ete: Redis key to store start time of time calculation
    :param key_exception: Redis key where exception information is stored
    :param key_current: Redis key containing progressed items count
    :param key_total: Redis key containing total to progress item count
    """
    if int(redis_con.get(key_run) or 0) == 1:
        redis_con.close()
        flask.abort(400, process_name + " already running")

    # (re)set Redis keys
    redis_con.set(key_run, 1)
    redis_con.set(key_time, int(datetime.timestamp(datetime.now())))
    redis_con.delete(key_time_ete)
    redis_con.delete(key_exception)
    redis_con.set(key_current, 0)
    redis_con.set(key_total, 0)
