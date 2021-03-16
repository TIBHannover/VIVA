import threading

from tensorflow import keras

from common.SharedUtils import create_redis_connection, sse_send_training_data
from common.SharedValues import SharedValues
from common.consts import *


class RedisSSECallback(keras.callbacks.Callback):
    def __init__(self, sv_instance: SharedValues, steps_per_epoch: int):
        super().__init__()
        self._redis_con = create_redis_connection()
        self._sv_instance = sv_instance
        self._steps_per_epoch = steps_per_epoch
        self._step = 0
        self._epoch_m1 = 0

    def on_batch_end(self, batch, logs=None):
        self._step += 1
        if self._step % int(os.environ['TRAINING_SSE_UPDATE_STEPS']) == 0:
            self._redis_con.set(os.environ['REDIS_KEY_TRAINING_CURRENT'], self._epoch_m1 * self._steps_per_epoch +
                                self._step)
            threading.Thread(target=sse_send_training_data, args=(self._sv_instance, self._redis_con)).start()

    def on_epoch_end(self, epoch, logs=None):
        self._epoch_m1 += 1
        self._step = 0
        self._redis_con.set(os.environ['REDIS_KEY_TRAINING_CURRENT'], self._epoch_m1 * self._steps_per_epoch)
        self._redis_con.rpush(os.environ['REDIS_KEY_TRAINING_MAP'], logs['mean_average_precision'].item())
        self._redis_con.rpush(os.environ['REDIS_KEY_TRAINING_LOSS'], logs['loss'])
        self._redis_con.rpush(os.environ['REDIS_KEY_TRAINING_LR'],
                              float(keras.backend.get_value(self.model.optimizer.lr)))
        threading.Thread(target=sse_send_training_data, args=(self._sv_instance, self._redis_con)).start()

    def on_train_end(self, logs=None):
        self._redis_con.close()


# class ValidationRedisSSECallback(keras.callbacks.Callback):
#     def __init__(self, sv_instance: SharedValues):
#         super().__init__()
#         self._redis_con = create_redis_connection()
#         self._sv_instance = sv_instance
#         self._start_steps = self._redis_con.get(os.environ['REDIS_KEY_TRAINING_CURRENT'])
#         self._step = 0
#
#     def on_predict_batch_end(self, batch, logs=None):
#         self._step += 1
#         if (self._start_steps + self._step) % int(os.environ['TRAINING_SSE_UPDATE_STEPS']) == 0:
#             self._redis_con.set(os.environ['REDIS_KEY_TRAINING_CURRENT'], self._start_steps + self._step)
#             threading.Thread(target=sse_send_training_data, args=(self._sv_instance, self._redis_con)).start()
