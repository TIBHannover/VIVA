import os

import redis
from flask import Flask, jsonify
from flask_cors import CORS

from common.SharedUtils import create_redis_pool, sse_send_inference_data, sse_send_training_data
from common.SharedValues import SharedValues
from common.consts import FILE_PATH_LOG_TRAINING, FILE_PATH_LOG_INFERENCE
from flask_app.SSEBlueprintNginx import SSEBlueprintNginx, sse_nginx
from flask_app.control.Export import start_export, stop_export, update_export
from flask_app.control.Inference import start_inference, stop_inference
from flask_app.control.Training import start_training, stop_training
from flask_app.info import get_log_file
from flask_app.info.Training import basic_info


def get_sse_app(sv_instance: SharedValues = None):
    """Create an instance of the flask app

    :param sv_instance: An instance of SharedValue to provide access to shared memory.
                        Might be None if only app context is needed for SSE publishing (no flask serving)
    :return: an instance of the flask app
    """
    flask_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app = Flask(__name__)

    # Allow ajax requests from another host (required on development)
    if flask_debug:
        CORS(app, origins=["http://localhost:" + os.getenv("PORT_DJANGO", "8000"),
                           "http://127.0.0.1:" + os.getenv("PORT_DJANGO", "8000")])

    app.config['REDIS_URL'] = "redis://" + os.environ['SERVICE_DATABASE_REDIS'] + ":6379/" \
                              + str(os.environ['REDIS_DB_FLASK_SSE'])
    app.register_blueprint(sse_nginx, url_prefix='/' + os.environ['FLASK_URL_SSE'])

    # more configuration is not required for SSE
    if not sv_instance:
        return app

    redis_pool = create_redis_pool()

    @app.route("/basic_info")
    def get_basic_info():
        return jsonify(basic_info(redis_pool, sv_instance))

    # # # Training # # #
    @app.route(os.environ['FLASK_URL_TRAINING_START'], methods=['POST'])
    def training_start():
        start_training(redis_pool, sv_instance)
        return ""

    @app.route(os.environ['FLASK_URL_TRAINING_STOP'], methods=["POST"])
    def training_stop():
        stop_training(redis_pool, sv_instance)
        return ""

    @app.route(os.environ['FLASK_URL_TRAINING_UPDATE'], methods=["POST"])
    def training_update():
        redis_con = redis.Redis(connection_pool=redis_pool)
        sse_send_training_data(sv_instance, redis_con)
        redis_con.close()
        return ""

    @app.route(os.environ['FLASK_URL_TRAINING_LOG'])
    def training_log():
        return get_log_file(FILE_PATH_LOG_TRAINING)

    # # # Inference # # #
    @app.route(os.environ['FLASK_URL_INFERENCE_START'], methods=['POST'])
    def inference_start():
        start_inference(redis_pool, sv_instance)
        return ""

    @app.route(os.environ['FLASK_URL_INFERENCE_STOP'], methods=["POST"])
    def inference_stop():
        stop_inference(redis_pool, sv_instance)
        return ""

    @app.route(os.environ['FLASK_URL_INFERENCE_UPDATE'], methods=["POST"])
    def inference_update():
        redis_con = redis.Redis(connection_pool=redis_pool)
        sse_send_inference_data(sv_instance, redis_con)
        redis_con.close()
        return ""

    @app.route(os.environ['FLASK_URL_INFERENCE_LOG'])
    def inference_log():
        return get_log_file(FILE_PATH_LOG_INFERENCE)

    # # # Export # # #
    @app.route(os.environ['FLASK_URL_EXPORT_START'], methods=["POST"])
    def export_start():
        start_export(redis_pool, sv_instance)
        return ""

    @app.route(os.environ['FLASK_URL_EXPORT_STOP'], methods=["POST"])
    def export_stop():
        stop_export(redis_pool, sv_instance)
        return ""

    @app.route(os.environ['FLASK_URL_EXPORT_UPDATE'], methods=["POST"])
    def export_fr_update():
        update_export(redis_pool, sv_instance)
        return ""

    @app.errorhandler(400)
    def custom400(error):
        response = jsonify({'message': error.description})
        response.status_code = 400
        return response

    return app
