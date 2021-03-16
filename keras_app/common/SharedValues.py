import multiprocessing
from typing import Dict, List

import flask

from .consts import DJANGO_APP_NAMES


class SeparatedProcessEvents:
    def __init__(self):
        self.start: multiprocessing.Event = multiprocessing.Event()
        self.stop: multiprocessing.Event = multiprocessing.Event()


class SharedValues:
    flask_app: flask.Flask = None
    compatible_gpus: List[int] = []

    def __init__(self):
        self.training: SeparatedProcessEvents = SeparatedProcessEvents()
        self.inference: SharedValues.Inference = SharedValues.Inference()
        self.export: Dict[str, SeparatedProcessEvents] = {}
        for django_app_name in DJANGO_APP_NAMES:
            self.export[django_app_name] = SeparatedProcessEvents()

    class Inference(SeparatedProcessEvents):
        def __init__(self):
            super().__init__()
            self.running = multiprocessing.Value('B', 0)  # required to stop internal multiprocessing
            self.num_finished = multiprocessing.Value('L')  # count processed images (multiprocessing)
