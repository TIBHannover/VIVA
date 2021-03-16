import re
import socket
import time
from typing import Union, Callable

import psycopg2
import psycopg2.extensions
import psycopg2.pool
import redis
from flask_sse import sse

from .SharedValues import *
from .consts import *


def set_separated_process_stop(redis_con: redis.Redis, redis_key_run: str, redis_key_time: str,
                               redis_key_exception: str, container_start: bool = False, exception: str = None) -> None:
    """Sets Redis keys for a separated process (training, inference, export) to stopped values and does time calculation
    if required

    :param redis_con: an instance of Redis connection
    :param redis_key_run: the redis key that indicates that the process is running
    :param redis_key_time: the redis key that contains the information about runtime
    :param redis_key_exception: the redis key that contains the exception if any occurred
    :param container_start: true if this method got called on service start
    :param exception: the exception that occurred that forced the process to stop
    """
    if container_start:
        if redis_con.get(redis_key_run) == "1":
            redis_con.delete(redis_key_time)
            redis_con.set(redis_key_exception, "Container was stopped during run")
    elif redis_con.get(redis_key_run) == "1":
        redis_con.set(redis_key_time, int(datetime.timestamp(datetime.now())) - int(redis_con.get(redis_key_time)))
        if exception is not None:
            redis_con.set(redis_key_exception, exception)
    redis_con.set(redis_key_run, 0)


def set_training_stop(redis_con: redis.Redis, sv_instance: SharedValues, container_start: bool = False,
                      exception: str = None):
    set_separated_process_stop(redis_con,
                               os.environ['REDIS_KEY_TRAINING_RUN'],
                               os.environ['REDIS_KEY_TRAINING_TIME'],
                               os.environ['REDIS_KEY_TRAINING_EXCEPTION'],
                               container_start,
                               exception)
    sse_send_training_data(sv_instance, redis_con)


def set_inference_stop(redis_con: redis.Redis, sv_instance: SharedValues, container_start: bool = False,
                       exception: str = None):
    set_separated_process_stop(redis_con,
                               os.environ['REDIS_KEY_INFERENCE_RUN'],
                               os.environ['REDIS_KEY_INFERENCE_TIME'],
                               os.environ['REDIS_KEY_INFERENCE_EXCEPTION'],
                               container_start,
                               exception)
    sv_instance.inference.running.value = 0
    sse_send_inference_data(sv_instance, redis_con)
    sse_send_export_data(sv_instance, os.environ['DJANGO_APP_NAME_CONCEPT'], redis_con)


def set_export_stop(redis_con: redis.Redis, sv_instance: SharedValues, app_name: str, container_start: bool = False,
                    exception: str = None):
    set_separated_process_stop(redis_con,
                               os.environ['REDIS_KEY_EXPORT_RUN'].format(app_name),
                               os.environ['REDIS_KEY_EXPORT_TIME'].format(app_name),
                               os.environ['REDIS_KEY_EXPORT_EXCEPTION'].format(app_name),
                               container_start,
                               exception)
    sse_send_export_data(sv_instance, app_name, redis_con)
    if app_name == os.environ['DJANGO_APP_NAME_CONCEPT']:
        sse_send_inference_data(sv_instance, redis_con)


def create_redis_pool() -> redis.ConnectionPool:
    return redis.ConnectionPool(host=os.environ.get('SERVICE_DATABASE_REDIS'), db=os.environ.get('REDIS_DB_TRAIN'),
                                decode_responses=True)


def create_redis_connection() -> redis.Redis:
    return redis.Redis(host=os.environ.get('SERVICE_DATABASE_REDIS'), db=os.environ.get('REDIS_DB_TRAIN'),
                       decode_responses=True)


def create_postgres_pool() -> psycopg2.pool.ThreadedConnectionPool:
    return psycopg2.pool.ThreadedConnectionPool(1, 5, database=os.environ["POSTGRES_DB"],
                                                user=os.environ["POSTGRES_USER"],
                                                password=os.environ["POSTGRES_PASSWORD"],
                                                host=os.environ["SERVICE_DATABASE_POSTGRES"])


# noinspection PyProtectedMember
def create_postgres_connection() -> psycopg2._psycopg.connection:
    return psycopg2.connect(database=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
                            password=os.environ["POSTGRES_PASSWORD"], host=os.environ["SERVICE_DATABASE_POSTGRES"])


def get_redis_number_list(redis_con: redis.Redis, redis_key: str, floats: bool = False) -> List[int]:
    """Returns a list of numbers that are stored in Redis (numbers do not exist in Redis - always strings)

    :param redis_con: an instance of Redis connection
    :param redis_key: the Redis key
    :param floats: true if the list should be converted to float instead of int
    :return: the list of numbers
    """
    return list(map(lambda x: float(x) if floats else int(x), redis_con.lrange(redis_key, 0, -1)))


def wait_for_port(port, host='localhost', timeout=5.0):
    # https://gist.github.com/butla/2d9a4c0f35ea47b7452156c96a4e7b12
    """Wait until a port starts accepting TCP connections.
    Args:
        port (int): Port number.
        host (str): Host address on which the port should exist.
        timeout (float): In seconds. How long to wait before raising errors.
    Raises:
        TimeoutError: The port isn't accepting connection after time specified in `timeout`.
    """
    start_time = time.perf_counter()
    while True:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                break
        except OSError as ex:
            time.sleep(0.01)
            if time.perf_counter() - start_time >= timeout:
                raise TimeoutError('Waited too long for the port {} on host {} to start accepting '
                                   'connections.'.format(port, host)) from ex


def get_gpu_info_reduced(redis_con: redis.Redis, gpus_compat: List[int], training: bool) -> Dict[str, List[dict]]:
    """Return a reduced dictionary containing information about GPUs grouped by GPU names. This method will not
    utilize the nvml interface which reduces time (compared to old implementation).

    :param redis_con: an instance of Redis connection
    :param gpus_compat: a list of GPUs that are compatible with TensorFlow
    :param training: true if GPU information for training - for inference if false
    :return: dictionary that contains GPU names as key and list of dictionaries with GPU information as values
    """
    gpu_data = {}
    gpu_name_list = redis_con.lrange(os.environ['REDIS_KEY_GPU_NAMES'], 0, -1)
    gpu_ok_list = get_redis_number_list(redis_con, os.environ[
        'REDIS_KEY_TRAINING_GPUS_OK' if training else 'REDIS_KEY_INFERENCE_GPUS_OK'])
    for gpu_i, gpu_name in enumerate(gpu_name_list):
        if gpu_name not in gpu_data:
            gpu_data[gpu_name] = []
        gpu_data[gpu_name].append({
            'index': gpu_i,
            'ok': gpu_i in gpu_ok_list,
            'tf_comp': gpu_i in gpus_compat
        })
    return gpu_data


def get_export_files(cc_app: bool, model_ident: str) -> List[Dict[str, Union[str, int]]]:
    """Returns a list of objects representing the current available export files based on given file identifier

    :param cc_app: true if Django app is concept classification
    :param model_ident: The model identifier for exported files
    :return: List of dictionaries that contain information about export files
    """
    file_ident = "{:s}_{:s}".format(
        os.environ['EXPORT_FILE_PREFIX_CC'] if cc_app else os.environ['EXPORT_FILE_PREFIX_FR'], model_ident or "")
    files = []
    for file_name in sorted(os.listdir(os.environ['EXPORT_MOUNT_PATH'])):
        if not file_name.startswith(file_ident):
            continue
        file_path = os.path.join(os.environ['EXPORT_MOUNT_PATH'], file_name)
        files.append({
            'filename': file_name,
            'date': re.sub(r"\.(\d+)$", "", datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(sep=' ')),
            'threshold': int(re.match(r".+_(\d{2,3})\.zip$", file_name).groups()[0]),
            'size': os.path.getsize(file_path)
        })
    return files


def sse_get_standard_information(redis_con: redis.Redis, env_redis_key_part: str,
                                 env_map_func: Callable[[str], str] = lambda x: x) -> Dict[str, Union[str, int]]:
    """Returns a dictionary containing the basic information to send to clients using SSE

    :param redis_con: an instance of Redis connection
    :param env_redis_key_part: the part of the environment variable that differs
    :param env_map_func: an optional function that will be mapped on environment variables
    :return: dictionary containing the basic information
    """
    return {
        os.environ['ASYNC_ACTION_KEY_RUN']:
            int(redis_con.get(env_map_func(os.environ[f"REDIS_KEY_{env_redis_key_part}_RUN"])) or 0) == 1,
        os.environ['ASYNC_ACTION_KEY_TIME']:
            int(redis_con.get(env_map_func(os.environ[f"REDIS_KEY_{env_redis_key_part}_TIME"])) or -1),
        os.environ['ASYNC_ACTION_KEY_TIME_ETE']:
            int(redis_con.get(env_map_func(os.environ[f"REDIS_KEY_{env_redis_key_part}_TIME_ETE"])) or -1),
        os.environ['ASYNC_ACTION_KEY_EXCEPTION']:
            redis_con.get(env_map_func(os.environ[f"REDIS_KEY_{env_redis_key_part}_EXCEPTION"])),
        os.environ['ASYNC_ACTION_KEY_CURRENT']:
            int(redis_con.get(env_map_func(os.environ[f"REDIS_KEY_{env_redis_key_part}_CURRENT"])) or 0),
        os.environ['ASYNC_ACTION_KEY_TOTAL']:
            int(redis_con.get(env_map_func(os.environ[f"REDIS_KEY_{env_redis_key_part}_TOTAL"])) or 0),
    }


def sse_send_training_data(sv_instance: SharedValues, redis_con: redis.Redis) -> None:
    """Send all required information about training to clients using server side events

    :param sv_instance: an instance of SharedValues
    :param redis_con: an instance of Redis connection
    """
    running = int(redis_con.get(os.environ['REDIS_KEY_TRAINING_RUN']) or 0) == 1
    with sv_instance.flask_app.app_context():
        sse.publish({
            **sse_get_standard_information(redis_con, "TRAINING"),
            os.environ['ASYNC_ACTION_KEY_OPTIONS']: {
                'batch_size': int(redis_con.get(os.environ['REDIS_KEY_TRAINING_BATCH_SIZE'])) if running else None,
                'gpu_selection': get_redis_number_list(redis_con, os.environ['REDIS_KEY_TRAINING_GPUS'])
                if running and GPU_MODE else None,
                'gpu_info': get_gpu_info_reduced(redis_con, sv_instance.compatible_gpus, training=True)
                if GPU_MODE else None
            },
            'steps_per_epoch': int(redis_con.get(os.environ['REDIS_KEY_TRAINING_STEPS_PER_EPOCH']) or 1),
            'charts': {
                'map': get_redis_number_list(redis_con, os.environ['REDIS_KEY_TRAINING_MAP'], floats=True),
                'loss': get_redis_number_list(redis_con, os.environ['REDIS_KEY_TRAINING_LOSS'], floats=True),
                'lr': get_redis_number_list(redis_con, os.environ['REDIS_KEY_TRAINING_LR'], floats=True)
            }
        }, type=os.environ['FLASK_SSE_TRAINING_INFO'])


def sse_send_inference_data(sv_instance: SharedValues, redis_con: redis.Redis) -> None:
    """Send all required information about inference to clients using server side events

    :param sv_instance: an instance of SharedValues
    :param redis_con: an instance of Redis connection
    """
    postgres_con = create_postgres_connection()
    prerequisite_cur = postgres_con.cursor()
    prerequisite_cur.execute("""
        SELECT * 
        FROM evaluation 
        JOIN class c on c.id = evaluation.classid 
        WHERE classtypeid = %s 
        LIMIT 1""", (os.environ['DB_CLTP_ID_CONCEPT'],))
    running = int(redis_con.get(os.environ['REDIS_KEY_INFERENCE_RUN']) or 0) == 1
    with sv_instance.flask_app.app_context():
        sse.publish({
            **sse_get_standard_information(redis_con, "INFERENCE"),
            os.environ['ASYNC_ACTION_KEY_DEPENDENCY_RUN']: int(redis_con.get(
                os.environ['REDIS_KEY_EXPORT_RUN'].format(os.environ['DJANGO_APP_NAME_CONCEPT'])) or 0) == 1,
            os.environ['ASYNC_ACTION_KEY_DEPENDENCY_PRE']: prerequisite_cur.fetchone() is None,
            os.environ['ASYNC_ACTION_KEY_OPTIONS']: {
                'batch_size': int(redis_con.get(os.environ['REDIS_KEY_INFERENCE_BATCH_SIZE'])) if running else None,
                'gpu_selection': get_redis_number_list(redis_con, os.environ['REDIS_KEY_INFERENCE_GPUS'])
                if running and GPU_MODE else None,
                'gpu_info': get_gpu_info_reduced(redis_con, sv_instance.compatible_gpus, training=False)
                if GPU_MODE else None
            },
        }, type=os.environ['FLASK_SSE_INFERENCE_INFO'])
    prerequisite_cur.close()
    postgres_con.close()


def sse_send_export_data(sv_instance: SharedValues, app_name: str, redis_con: redis.Redis) -> None:
    """Send all required information about export to clients using server side events

    :param sv_instance: an instance of SharedValues
    :param app_name: the name of current Django app
    :param redis_con: a redis connection
    """
    is_cc_app = app_name == os.environ['DJANGO_APP_NAME_CONCEPT']
    postgres_con = create_postgres_connection()
    prerequisite_cur = postgres_con.cursor()
    prerequisite_cur.execute("""
        SELECT * 
        FROM model
        JOIN imageprediction i on model.id = i.modelid
        JOIN class c on c.id = i.classid 
        WHERE classtypeid = %s
        AND inference_stored = true
        LIMIT 1""", (int(os.environ['DB_CLTP_ID_CONCEPT'] if is_cc_app else os.environ['DB_CLTP_ID_PERSON']),))
    running = int(redis_con.get(os.environ['REDIS_KEY_EXPORT_RUN'].format(app_name)) or 0) == 1
    model_ident = redis_con.get(os.environ['REDIS_KEY_EXPORT_MODEL_IDENT'].format(app_name))
    with sv_instance.flask_app.app_context():
        sse.publish({
            **sse_get_standard_information(redis_con, "EXPORT", lambda x: x.format(app_name)),
            os.environ['ASYNC_ACTION_KEY_DEPENDENCY_RUN']:
            # TODO: implement for face recognition app
                (int(redis_con.get(os.environ['REDIS_KEY_INFERENCE_RUN']) or 0) == 1) if is_cc_app else 0,
            os.environ['ASYNC_ACTION_KEY_DEPENDENCY_PRE']: prerequisite_cur.fetchone() is None,
            os.environ['ASYNC_ACTION_KEY_OPTIONS']: {
                'threshold': int(
                    redis_con.get(os.environ['REDIS_KEY_EXPORT_THRESHOLD'].format(app_name))) if running else None
            },
            'last_model': model_ident,
            'files': get_export_files(is_cc_app, model_ident) if model_ident else None
        }, type=os.environ['FLASK_SSE_EXPORT_INFO'].format(app_name))
    prerequisite_cur.close()
    postgres_con.close()
