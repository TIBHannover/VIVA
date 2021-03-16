import multiprocessing
import os

import redis
from flask import request, abort

from common.SharedUtils import set_export_stop, sse_send_export_data, sse_send_inference_data
from flask_app.control import redis_reset_startup
from common.SharedValues import SharedValues
from common.consts import DJANGO_APP_NAMES

export_start_lock: multiprocessing.Lock = multiprocessing.Lock()


def start_export(redis_pool: redis.ConnectionPool, sv_instance: SharedValues) -> None:
    # input validation
    if any(x not in request.form for x in ["threshold", "app"]):
        abort(400, "Missing parameter")
    try:
        threshold = int(request.form['threshold'])
        if threshold < 0 or threshold > 100:
            raise ValueError()
    except ValueError:
        abort(400, "Wrong parameter value")
        return  # senseless but avoids warning
    app_name = request.form['app']
    if app_name not in DJANGO_APP_NAMES:
        abort(400, "Wrong parameter value")

    # check run conditions
    redis_con = redis.Redis(connection_pool=redis_pool)
    if app_name == os.environ['DJANGO_APP_NAME_CONCEPT'] and \
            (redis_con.get(os.environ['REDIS_KEY_INFERENCE_RUN']) or "0") == "1":
        redis_con.close()
        abort(400, "Inference is currently running")

    with export_start_lock:
        redis_reset_startup(redis_con, "Export",
                            os.environ['REDIS_KEY_EXPORT_RUN'].format(app_name),
                            os.environ['REDIS_KEY_EXPORT_TIME'].format(app_name),
                            os.environ['REDIS_KEY_EXPORT_TIME_ETE'].format(app_name),
                            os.environ['REDIS_KEY_EXPORT_EXCEPTION'].format(app_name),
                            os.environ['REDIS_KEY_EXPORT_CURRENT'].format(app_name),
                            os.environ['REDIS_KEY_EXPORT_TOTAL'].format(app_name))
        redis_con.set(os.environ['REDIS_KEY_EXPORT_THRESHOLD'].format(app_name), threshold)

        # set event in shared memory for export start
        sv_instance.export[app_name].start.set()

    sse_send_export_data(sv_instance, app_name, redis_con)
    if app_name == os.environ['DJANGO_APP_NAME_CONCEPT']:
        sse_send_inference_data(sv_instance, redis_con)
    redis_con.close()


def stop_export(redis_pool: redis.ConnectionPool, sv_instance: SharedValues) -> None:
    # input validation
    if "app" not in request.form:
        abort(400, "Missing parameter")
    app_name = request.form['app']
    if app_name not in DJANGO_APP_NAMES:
        abort(400, "Wrong parameter value")

    redis_con = redis.Redis(connection_pool=redis_pool)
    if int(redis_con.get(os.environ['REDIS_KEY_EXPORT_RUN'].format(app_name)) or 0) == 1:
        sv_instance.export[app_name].stop.set()
        set_export_stop(redis_con, sv_instance, app_name, exception="User canceled export run")
    redis_con.close()


def update_export(redis_pool: redis.ConnectionPool, sv_instance: SharedValues) -> None:
    # input validation
    if "app" not in request.form:
        abort(400, "Missing parameter")
    app_name = request.form['app']
    if app_name not in DJANGO_APP_NAMES:
        abort(400, "Wrong parameter value")

    redis_con = redis.Redis(connection_pool=redis_pool)
    sse_send_export_data(sv_instance, app_name, redis_con)
    redis_con.close()
