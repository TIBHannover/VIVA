import concurrent.futures
import threading
import time
from datetime import datetime

from flask_sse import sse

from common.SharedUtils import sse_send_inference_data, create_redis_connection, sse_send_training_data
from common.SharedValues import SharedValues
from common.consts import GPU_MODE, SSE_TYPE_HW_INFO
from hw_info import write_initial_gpu_info, get_gpu_info, get_cpu_info


def broadcast_sys_info(sv_instance: SharedValues):
    redis_con = create_redis_connection()
    write_initial_gpu_info(redis_con)
    while True:
        time_start = int(datetime.now().timestamp())
        cpu_future = concurrent.futures.ThreadPoolExecutor().submit(get_cpu_info)
        gpu_future = concurrent.futures.ThreadPoolExecutor().submit(get_gpu_info, redis_con,
                                                                    sv_instance.compatible_gpus)
        cpu_info = cpu_future.result(5)
        gpu_info = gpu_future.result(5)
        with sv_instance.flask_app.app_context():
            sse.publish({
                "cpu": cpu_info,
                "gpu": gpu_info[0],
                "gpu_support": GPU_MODE
            }, type=SSE_TYPE_HW_INFO)
        if gpu_info[1]:
            threading.Thread(target=sse_send_training_data, args=(sv_instance, redis_con)).start()
        if gpu_info[2]:
            threading.Thread(target=sse_send_inference_data, args=(sv_instance, redis_con)).start()
        time_diff = time_start + 1 - datetime.now().timestamp()
        if time_diff > 0:
            time.sleep(time_diff)