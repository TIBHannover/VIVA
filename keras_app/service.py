import signal
import sys

import pynvml
import requests

import export
import flask_app
import hw_info
import hw_info.SSEUpdater
import inference
import training
from common.SharedUtils import *
from common.SharedValues import *
from flask_app import gunicorn_app

HOST_NAME = '0.0.0.0'
PORT_NUMBER = 8080
LOG_TIME = "%Y-%m-%d %H:%M:%S "


# noinspection PyUnusedLocal
def sigterm_handler(signal_rec, frame):
    print(time.strftime(LOG_TIME), "Received stop signal - sending interrupt to started sub processes...")
    os.kill(process_flask.pid, signal.SIGINT)
    os.kill(process_hw_mon.pid, signal.SIGINT)
    stop_training_process()
    stop_inference_process()
    sys.exit(0)


def create_process(target, sv: SharedValues):
    return multiprocessing.Process(target=target, args=(sv,))


def set_compatible_tf_gpus(sv: SharedValues):
    def get_comp_tf_dev(queue: multiprocessing.Queue):
        """Set the list of GPU indices that are compatible to used TensorFlow version
        Use with care. This function is not allowed to be called on main process otherwise other processes will fail to
        utilize the GPU.

        :param queue: Multiprocessing queue where GPU indices will be put
        """
        import tensorflow as tf
        for comp_gpu in tf.config.list_physical_devices('GPU'):
            # TODO: Index might not match in system with mixed graphic cards?
            queue.put(int(re.search(r"(?P<index>\d+)$", comp_gpu.name).group("index")))

    result = multiprocessing.Queue()
    tf_comp_gpu_proc = multiprocessing.Process(target=get_comp_tf_dev, args=(result,))
    tf_comp_gpu_proc.start()
    tf_comp_gpu_proc.join()
    sv.compatible_gpus += [result.get(block=False) for _ in range(result.qsize())]
    print("TensorFlow compatible GPUs:", sv.compatible_gpus)


def run_flask_process(sv: SharedValues):
    print(time.strftime(LOG_TIME), "Flask server starts - %s:%s" % (HOST_NAME, PORT_NUMBER))
    try:
        from gevent import monkey
        # Avoid issue https://github.com/gevent/gevent/issues/1016
        # Patching on service process level leads to errors on TensorFlow training
        monkey.patch_all()
        options = {
            'bind': '{:s}:{:d}'.format(HOST_NAME, PORT_NUMBER)
        }
        gunicorn_app.SSEApp(flask_app.get_sse_app(sv), options).run()  # gunicorn requires own instance of flask app
    except KeyboardInterrupt:
        print(time.strftime(LOG_TIME), "Flask server stops - %s:%s" % (HOST_NAME, PORT_NUMBER))


def run_hardware_monitor(sv: SharedValues):
    print(time.strftime(LOG_TIME), "Hardware monitoring starts")
    try:
        if GPU_MODE:
            pynvml.nvmlInit()
        hw_info.SSEUpdater.broadcast_sys_info(sv)
    except KeyboardInterrupt:
        print(time.strftime(LOG_TIME), "Hardware monitoring stops")
        if GPU_MODE:
            pynvml.nvmlShutdown()


def run_train_process(sv: SharedValues):
    print(time.strftime(LOG_TIME), "Training starts")
    redis_connection = create_redis_connection()
    set_gpu_env_variable(get_redis_number_list(redis_connection, os.environ['REDIS_KEY_TRAINING_GPUS']))
    redis_connection.close()
    training.start_train(sv)
    print(time.strftime(LOG_TIME), "Training stops")


def run_inference_process(sv: SharedValues):
    print(time.strftime(LOG_TIME), "Inference starts")
    inference.start_inference(sv)
    print(time.strftime(LOG_TIME), "Inference stops")


def run_export_process(app_name: str, sv: SharedValues):
    print(time.strftime(LOG_TIME), "Export for", app_name, "starts")
    export.start_export(sv, app_name)
    print(time.strftime(LOG_TIME), "Export for", app_name, "stops")


def stop_training_process():
    if process_train and process_train.pid:
        os.kill(process_train.pid, signal.SIGINT)
        time.sleep(2)
        os.kill(process_train.pid, signal.SIGKILL)


def stop_inference_process():
    if process_inference and process_inference.pid:
        os.kill(process_inference.pid, signal.SIGINT)
        time.sleep(2)
        os.kill(process_inference.pid, signal.SIGKILL)


def stop_export_process(app_name: str):
    if app_name in process_export:
        exp_process = process_export[app_name]
        if exp_process and exp_process.pid:
            os.kill(exp_process.pid, signal.SIGINT)
            time.sleep(2)
            os.kill(exp_process.pid, signal.SIGKILL)


def set_gpu_env_variable(gpu_selection: list):
    cuda_visible_device_string = ""
    if len(gpu_selection) > 0:
        cuda_visible_device_string += str(gpu_selection[0])
        for gpu_device in gpu_selection[1:]:
            cuda_visible_device_string += "," + str(gpu_device)
    os.environ["CUDA_VISIBLE_DEVICES"] = cuda_visible_device_string


def check_tfs_http_availability() -> bool:
    try:
        wait_for_port(8000, os.environ["SERVICE_TFS_APP"], 15)
    except TimeoutError as te:
        print(te)
        print("Cannot reach TensorFlow Serving http app ... is the container up and running?")
        return False
    return True


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, sigterm_handler)

    shared_values_instance = SharedValues()
    shared_values_instance.flask_app = flask_app.get_sse_app(None)
    set_compatible_tf_gpus(shared_values_instance)

    redis_con = create_redis_connection()
    set_training_stop(redis_con, shared_values_instance, True)
    set_inference_stop(redis_con, shared_values_instance, True)
    for da_name in DJANGO_APP_NAMES:
        set_export_stop(redis_con, shared_values_instance, da_name, True)
    redis_con.close()

    process_flask = create_process(run_flask_process, shared_values_instance)
    process_flask.start()
    process_hw_mon = create_process(run_hardware_monitor, shared_values_instance)
    process_hw_mon.start()
    process_train = process_inference = None

    process_export = {}
    inference_running = False  # does not reflect the real state if the inference stops expectedly this will stay true
    tfs_running = True

    while True:
        time.sleep(1)

        # flask process
        if not process_flask.is_alive():
            process_flask = create_process(run_flask_process, shared_values_instance)
            process_flask.start()

        # HW info process
        if not process_hw_mon.is_alive():
            process_hw_mon = create_process(run_hardware_monitor, shared_values_instance)
            process_hw_mon.start()

        # training process
        if shared_values_instance.training.start.is_set():
            if shared_values_instance.training.stop.is_set():
                shared_values_instance.training.stop.clear()
            else:
                process_train = create_process(run_train_process, shared_values_instance)
                process_train.start()
            shared_values_instance.training.start.clear()
        if shared_values_instance.training.stop.is_set():
            stop_training_process()
            shared_values_instance.training.stop.clear()

        # inference process
        if shared_values_instance.inference.start.is_set():
            if shared_values_instance.inference.stop.is_set():
                shared_values_instance.inference.stop.clear()
            else:
                if check_tfs_http_availability():
                    tfs_running = inference_running = True
                    process_inference = create_process(run_inference_process, shared_values_instance)
                    process_inference.start()
                else:
                    set_inference_stop(redis_con, shared_values_instance,
                                       exception="TensorFlow serving cannot be started - service not available")
            shared_values_instance.inference.start.clear()
        if shared_values_instance.inference.stop.is_set():
            stop_inference_process()
            inference_running = False
            shared_values_instance.inference.stop.clear()

        # inference server stop control
        if tfs_running and not inference_running:
            if check_tfs_http_availability():
                requests.post("http://" + os.environ["SERVICE_TFS_APP"] + ":8000" + os.environ["URL_TFS_STOP"])
                tfs_running = False

        # export processes
        for da_name, sp_class in shared_values_instance.export.items():
            if sp_class.start.is_set():
                if sp_class.stop.is_set():
                    sp_class.stop.clear()
                else:
                    process_export[da_name] = create_process(lambda x: run_export_process(da_name, x),
                                                             shared_values_instance)
                    process_export[da_name].start()
                sp_class.start.clear()
            if sp_class.stop.is_set():
                stop_export_process(da_name)
                sp_class.stop.clear()
