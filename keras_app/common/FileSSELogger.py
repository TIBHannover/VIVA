import io
import shutil

from flask import Flask
from flask_sse import sse

from .consts import *


class FileSSELogger(io.StringIO):
    def __init__(self, file_name: str, app: Flask, sse_type: str):
        """This logger logs to a given file name and publishes the log over SSE

        :param file_name: the file name for the log file (written in FILE_PATH_LATEST_LOGS)
        :param app: an instance of the flask app (required for SSE)
        :param sse_type: type of SSE event for log publishing
        """
        super().__init__()
        self._file_name = file_name
        self._buffer_string = ""
        self._app = app
        self._sse_type = sse_type

        self._rotate_log()
        with self._app.app_context():
            sse.publish({os.environ['FLASK_SSE_KEY_LOG_CLEAR']: True}, type=self._sse_type)
        self._file = open(os.path.join(FILE_PATH_LATEST_LOGS, file_name), 'x')

    def _rotate_log(self):
        """Rotates the log files with the same file name (using suffix '.X' where X = rotation number)

        """
        os.makedirs(FILE_PATH_LATEST_LOGS, exist_ok=True)
        for old, new in [("" if i == 0 else "." + str(i), "." + str(i + 1)) for i in
                         reversed(range(int(os.environ['LOG_ROTATION_PRESERVE_COUNT'])))]:
            if os.path.lexists(os.path.join(FILE_PATH_LATEST_LOGS, self._file_name + old)):
                os.rename(os.path.join(FILE_PATH_LATEST_LOGS, self._file_name + old),
                          os.path.join(FILE_PATH_LATEST_LOGS, self._file_name + new))  # also replaces file

    def write(self, s: str) -> int:
        if s in ["\n", "\r"]:
            self._file.write(self._buffer_string + "\n")
            self._file.flush()
            try:
                with self._app.app_context():
                    sse.publish({os.environ['FLASK_SSE_KEY_LOG_MESSAGE']: self._buffer_string}, type=self._sse_type)
            except Exception as _:
                pass
            self._buffer_string = ""
        else:
            self._buffer_string += s.replace("\x08", "")
        return super().write(s)

    def flush(self) -> None:
        self._file.flush()
        return super().flush()

    def close(self) -> None:
        self._file.close()
        return super().close()

    def copy_to(self, destination):
        """Copy log file to another directory

        :param destination: destination for log file copy
        """
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(os.path.join(FILE_PATH_LATEST_LOGS, self._file_name), destination)
