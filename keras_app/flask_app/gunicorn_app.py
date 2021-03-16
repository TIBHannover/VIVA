import multiprocessing
import os
from abc import ABC

import pynvml
from gunicorn.app.base import BaseApplication

from common.consts import GPU_MODE


def number_of_workers():
    return min(16, multiprocessing.cpu_count())


class SSEApp(BaseApplication, ABC):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.options['workers'] = number_of_workers()
        self.options['worker_class'] = "gunicorn.workers.ggevent.GeventWorker"
        if GPU_MODE:
            self.options['worker_exit'] = lambda server, worker: pynvml.nvmlShutdown()
        if 'FLASK_DEBUG' in os.environ and os.environ['FLASK_DEBUG'] == "1":
            self.options['accesslog'] = "-"
        self.application = app
        super(SSEApp, self).__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        if GPU_MODE:
            pynvml.nvmlInit()
        return self.application
