import multiprocessing
import os
import queue
import sys
import traceback

import grpc
import psycopg2.pool
import tensorflow as tf
import numpy as np
from psycopg2.extras import execute_values
from tensorflow_serving.apis import predict_pb2, prediction_service_pb2_grpc

from common.SharedUtils import create_postgres_pool
from common.SharedValues import SharedValues
from common.consts import DEFAULT_TARGET_SIZE


def prepare_request(batch_x) -> predict_pb2.PredictRequest:
    request = predict_pb2.PredictRequest()
    request.model_spec.name = os.environ["FILE_TFS_MODEL_DIR"]
    request.model_spec.signature_name = 'serving_default'
    request.inputs['input_1'].CopyFrom(tf.make_tensor_proto(
        batch_x, shape=[len(batch_x), DEFAULT_TARGET_SIZE[0], DEFAULT_TARGET_SIZE[1], 3]))
    return request


def process_result(batch_idx: int, batch_size: int, batch_x, data_ids: list, db_class_ids: list, model_id: int,
                   num_classes: int or None, postgres_pool: psycopg2.pool.ThreadedConnectionPool, result: np.array,
                   threshold_write_db: float):
    res = np.array(result.outputs['predictions'].float_val)
    if num_classes is None:
        num_classes = int(len(res) / len(batch_x))
    res = res.reshape((-1, num_classes))
    postgres_insert = []
    for img_res_idx, img_res in enumerate(res):
        img_id = None
        for pred_idx, class_res in enumerate(img_res):
            if class_res >= threshold_write_db:
                if img_id is None:
                    img_id = data_ids[batch_idx * batch_size + img_res_idx]
                postgres_insert.append((img_id, db_class_ids[pred_idx], model_id, class_res))
    if len(postgres_insert) > 0:
        postgres_con = postgres_pool.getconn()
        postgres_cur = postgres_con.cursor()
        execute_values(postgres_cur,
                       "INSERT INTO imageprediction (imageid, classid, modelid, score) VALUES %s",
                       postgres_insert)
        postgres_con.commit()
        postgres_cur.close()
        postgres_pool.putconn(postgres_con)


def print_failed_images(batch_idx: int, batch_size: int, data_ids: list, last_exception_repr: str,
                        last_exception_trace_back: str):
    failed_img_ids = []
    for i in range(batch_size):
        add_data_ids_idx = batch_idx * batch_size + i
        if add_data_ids_idx < len(data_ids):
            failed_img_ids.append(data_ids[add_data_ids_idx])
    print("=> Batch {:d} failed".format(batch_idx))
    print("Batch {:d} - image ids:".format(batch_idx), failed_img_ids)
    print("Batch {:d} - last exception:".format(batch_idx), last_exception_repr, file=sys.stderr)
    print("Batch {:d} - last traceback:\n".format(batch_idx), last_exception_trace_back,
          file=sys.stderr)


# TODO implement only stop after postgres commit
def process_batch_queue(batch_queue: multiprocessing.Queue, batch_size: int, model_id: int, data_ids: list,
                        db_class_ids: list, process_num: int, sv_instance: SharedValues):
    num_classes = None
    max_batch_retries = int(os.environ["INFERENCE_BATCH_MAX_RETRY"])
    threshold_write_db = float(os.environ["INFERENCE_THRESHOLD_DB_WRITE"])
    postgres_pool = create_postgres_pool()
    print("Worker {:d} - start".format(process_num))
    queue_timeout = 0
    while True:
        try:
            batch_idx, batch_x = batch_queue.get(timeout=2)
            queue_timeout = 0
            channel = grpc.insecure_channel(os.environ["SERVICE_TFS_APP"] + ":" + str(8500 + process_num))
            stub = prediction_service_pb2_grpc.PredictionServiceStub(channel)
            request = prepare_request(batch_x)
            batch_try_counter = 0
            while batch_try_counter <= max_batch_retries:
                if sv_instance.inference.running.value == 0:  # stop worker on inference "stop request"
                    print("Worker {:d} - stop".format(process_num))
                    return
                try:
                    result, _ = stub.Predict.with_call(request, timeout=60)
                    process_result(batch_idx, batch_size, batch_x, data_ids, db_class_ids, model_id, num_classes,
                                   postgres_pool, result, threshold_write_db)
                    break
                except Exception as exc:
                    print("ERROR: Inference failed for batch {:d} ({:d}/{:d}).".format(batch_idx, batch_try_counter + 1,
                                                                                       max_batch_retries))
                    print("Batch {:d} - ".format(batch_idx), repr(exc), file=sys.stderr)
                    last_exception_repr = str(repr(exc))
                    last_exception_trace_back = str(traceback.format_exc())
                batch_try_counter += 1
            if batch_try_counter > max_batch_retries:
                # noinspection PyUnboundLocalVariable
                print_failed_images(batch_idx, batch_size, data_ids, last_exception_repr, last_exception_trace_back)
            with sv_instance.inference.num_finished.get_lock():
                sv_instance.inference.num_finished.value += batch_size
        except queue.Empty:
            queue_timeout += 2
            if sv_instance.inference.running.value == 0 or queue_timeout >= int(os.environ['INFERENCE_CLIENT_TIMEOUT']):
                break
    print("Worker {:d} - stop".format(process_num))

    postgres_pool.closeall()
