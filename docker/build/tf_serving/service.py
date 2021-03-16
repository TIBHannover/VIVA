import http.server
import json
import multiprocessing
import os
import signal
import socketserver
import subprocess
import sys
import time

HOST = "0.0.0.0"
PORT = 8000
LOG_TIME = "%Y-%m-%d %H:%M:%S "


class SharedValues:
    def __init__(self):
        self.event_start = multiprocessing.Event()
        self.event_stop = multiprocessing.Event()
        self._manger = multiprocessing.Manager()
        self.gpu_selection = self._manger.list()

    def shutdown(self):
        self._manger.shutdown()


def create_tfs_control_handler(sv: SharedValues):
    class TFServingControlHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self._sv_instance = sv
            super().__init__(*args, **kwargs)

        def do_GET(self):
            self.send_response(404)
            self.end_headers()

        # noinspection PyPep8Naming
        # no failsafe implementation since no exposure to public or intern network only docker network
        # should only be accessed by software in another container
        def do_POST(self):
            if self.path == os.environ["URL_TFS_START"]:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                post_json = json.loads(post_data)
                self._sv_instance.gpu_selection[:] = []
                if os.environ["TFS_POST_JSON_GPUS"] in post_json:
                    for gpu_id in post_json[os.environ["TFS_POST_JSON_GPUS"]]:
                        self._sv_instance.gpu_selection.append(gpu_id)
                self._sv_instance.event_start.set()
                self.send_response(200)
            elif self.path == os.environ["URL_TFS_STOP"]:
                self._sv_instance.event_stop.set()
                self.send_response(200)
            else:
                self.send_response(404)
            self.end_headers()

    return TFServingControlHandler


# noinspection PyUnusedLocal
def sigterm_handler(signal_rec, frame):
    print(time.strftime(LOG_TIME), "Received stop signal - sending interrupt to sub processes...")
    if process_httpd.pid is not None:
        os.kill(process_httpd.pid, signal.SIGINT)
    for process_tfs in processes_tfs:
        stop_inference_process(process_tfs)
    sys.exit(0)


def serve_http(sv: SharedValues):
    # using only non production httpd service since it should only be exposed inside docker network
    # and never to the world
    print(time.strftime(LOG_TIME), "Python HTTP server starts - {}:{}".format(HOST, PORT))
    with socketserver.TCPServer((HOST, PORT), create_tfs_control_handler(sv)) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()
    print(time.strftime(LOG_TIME), "Python HTTP server stops")


def tf_serving(gpu_selection: list, idx: int):
    set_gpu_env_variable(gpu_selection)
    print(time.strftime(LOG_TIME), "TensorFlow Serving server ({:d}) starts".format(idx))
    try:
        print("CUDA_VISIBLE_DEVICES =", os.environ["CUDA_VISIBLE_DEVICES"])
        subprocess.run(["tensorflow_model_server", "--model_name=" + os.environ["FILE_TFS_MODEL_DIR"],
                        "--model_base_path=/models/" + os.environ["FILE_TFS_MODEL_DIR"], "--port=" + str(8500 + idx)])
    except KeyboardInterrupt:
        pass
    print(time.strftime(LOG_TIME), "TensorFlow Serving server ({:d}) stops".format(idx))


def create_tfs_processes(sv: SharedValues) -> list:
    processes = []
    for idx, gpu_id in enumerate(sv.gpu_selection):
        processes.append(multiprocessing.Process(target=tf_serving, args=([gpu_id], idx)))
    if len(sv.gpu_selection) == 0:
        processes.append(multiprocessing.Process(target=tf_serving, args=([], 0)))
    return processes


def set_gpu_env_variable(gpu_selection: list):
    cuda_visible_device_string = ""
    if len(gpu_selection) > 0:
        cuda_visible_device_string += str(gpu_selection[0])
        for gpu_device in gpu_selection[1:]:
            cuda_visible_device_string += "," + str(gpu_device)
    os.environ["CUDA_VISIBLE_DEVICES"] = cuda_visible_device_string


def stop_inference_process(process_tfs: multiprocessing.Process):
    if process_tfs is not None and process_tfs.pid is not None:
        os.kill(process_tfs.pid, signal.SIGINT)
        time.sleep(1)
        os.kill(process_tfs.pid, signal.SIGKILL)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, sigterm_handler)

    sv_instance = SharedValues()

    process_httpd = multiprocessing.Process(target=serve_http, args=(sv_instance,))
    process_httpd.start()

    processes_tfs = []

    while True:
        time.sleep(1)

        # httpd process
        if not process_httpd.is_alive():
            process_httpd = multiprocessing.Process(target=serve_http, args=(sv_instance,))
            process_httpd.start()

        # tf serving process
        if sv_instance.event_start.is_set():
            if sv_instance.event_stop.is_set():
                sv_instance.event_stop.clear()
            else:
                processes_tfs = create_tfs_processes(sv_instance)
                for proc in processes_tfs:
                    proc.start()
            sv_instance.event_start.clear()
        if sv_instance.event_stop.is_set():
            for proc in processes_tfs:
                stop_inference_process(proc)
            sv_instance.event_stop.clear()
