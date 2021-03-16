import os
from typing import List, Tuple

import pynvml
import redis

from common.SharedUtils import get_redis_number_list
from common.consts import GPU_MODE, RKEY_HWINFO_GPU_NAME, RKEY_HWINFO_GPU_MEM_AVAIL, RKEY_HWINFO_GPU_UTIL, \
    RKEY_HWINFO_GPU_MEM_USED, RKEY_HWINFO_GPU_TEMP


def db_update_available_gpus(redis_con: redis.Redis, redis_key: str, gpus_ok: List[int]) -> bool:
    original_set = set(get_redis_number_list(redis_con, redis_key))
    new_set = set(gpus_ok)
    to_delete = original_set - new_set
    to_add = new_set - original_set
    if len(to_delete) + len(to_add) == 0:
        return False
    [redis_con.lrem(redis_key, 1, idx) for idx in to_delete]
    [redis_con.lpush(redis_key, idx) for idx in to_add]
    return True


def get_gpu_info(redis_con: redis.Redis, gpus_compat: List[int]) -> Tuple[List[dict], bool, bool]:
    """Returns information about GPUs

    :param redis_con: an instance of Redis connection
    :param gpus_compat: a list of GPUs that are compatible with TensorFlow
    :return: Tuple that contains [0] list of dictionaries with information about every GPU
                                 [1] boolean that states if the available GPUs for training changed
                                 [2] boolean that states if the available GPUs for inference changed
    """
    if not GPU_MODE:
        return [], False, False
    gpu_data = []
    gpu_ok_train = []
    gpu_ok_inf = []
    for i in range(pynvml.nvmlDeviceGetCount()):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
        except pynvml.NVMLError:
            util = -1
        try:
            mem_use = pynvml.nvmlDeviceGetMemoryInfo(handle).used
        except pynvml.NVMLError:
            mem_use = -1
        try:
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        except pynvml.NVMLError:
            temp = -1
        mem_tot = int(redis_con.lindex(RKEY_HWINFO_GPU_MEM_AVAIL, i))
        if i in gpus_compat and mem_tot - mem_use >= int(os.environ['TRAINING_GPU_MIN_MEM']):
            gpu_ok_train.append(i)
        if i in gpus_compat and mem_tot - mem_use >= int(os.environ['INFERENCE_GPU_MIN_MEM']):
            gpu_ok_inf.append(i)
        gpu_data.append({
            'name': redis_con.lindex(RKEY_HWINFO_GPU_NAME, i),
            'index': i,
            'tf_compatibility': i in gpus_compat,
            'utilization': util,
            'memory': {
                'total': mem_tot,
                'used': mem_use
            },
            'temperature': temp
        })
    gpus_train_change = db_update_available_gpus(redis_con, os.environ['REDIS_KEY_TRAINING_GPUS_OK'], gpu_ok_train)
    gpus_inf_change = db_update_available_gpus(redis_con, os.environ['REDIS_KEY_INFERENCE_GPUS_OK'], gpu_ok_inf)
    return gpu_data, gpus_train_change, gpus_inf_change


def write_initial_gpu_info(redis_con: redis.Redis) -> None:
    """Write initial GPU information into database that are only required to be requested once on process startup.
    This is done to reduce the time requesting NVIDIAs interface by only requesting changing attributes. The following
    "static" attributes are requested in this method: name, total memory

    :param redis_con: an instance of Redis connection
    """
    redis_con.delete(RKEY_HWINFO_GPU_NAME)
    redis_con.delete(RKEY_HWINFO_GPU_MEM_AVAIL)
    if GPU_MODE:
        gpu_count = pynvml.nvmlDeviceGetCount()
        for i in range(16):
            if i >= gpu_count:
                redis_con.delete(RKEY_HWINFO_GPU_UTIL.format(i))
                redis_con.delete(RKEY_HWINFO_GPU_MEM_USED.format(i))
                redis_con.delete(RKEY_HWINFO_GPU_TEMP.format(i))
        for i in range(gpu_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            try:
                redis_con.lpush(RKEY_HWINFO_GPU_NAME, pynvml.nvmlDeviceGetName(handle).decode("utf-8"))
            except pynvml.NVMLError:
                redis_con.lpush(RKEY_HWINFO_GPU_NAME, "ERROR")
            try:
                redis_con.lpush(RKEY_HWINFO_GPU_MEM_AVAIL, pynvml.nvmlDeviceGetMemoryInfo(handle).total)
            except pynvml.NVMLError:
                redis_con.lpush(RKEY_HWINFO_GPU_MEM_AVAIL, -1)
