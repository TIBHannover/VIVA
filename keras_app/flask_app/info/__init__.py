import os

from flask import request, abort, make_response


def log_input_validation() -> int:
    """Validates the input for log file requests and returns the number for tail

    :return: the number for tail
    """
    tail = 0
    if "tail" in request.args:
        tail = int(request.args["tail"])
        if tail < 0 or tail > 1000000:
            abort(400, "Wrong parameter value for tail")
    return tail


def get_log_file(file_path: str) -> str:
    """Returns a response containing the (truncated) log file as "plain" text. Truncating is done by cutting of the last
     X lines of the file

    :param file_path: the file path to log file
    :return: response containing log content
    """
    tail = log_input_validation()

    if os.path.isfile(file_path):
        with open(file_path, 'r') as f:
            f_lines = f.readlines()
        response = make_response("".join(f_lines[-tail:]))
        response.headers['Content-Type'] = 'text/plain'
        return response
    return ""
