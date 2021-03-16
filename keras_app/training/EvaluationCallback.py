import numpy as np
import psycopg2
import tensorflow as tf
from psycopg2.extras import execute_values
from sklearn.metrics import average_precision_score
from tensorflow import keras

from common.SharedUtils import create_postgres_connection
from common.consts import *


class EvaluationCallback(keras.callbacks.Callback):

    def __init__(self, val_gen, class_map, start_time: int, save_model=True):
        super().__init__()
        self.val_gen = val_gen
        self.class_map = class_map
        self._start_time = start_time
        self.best_mean_ap = 0
        self.best_weights = None
        self.save_model = save_model
        self.average_precision_per_class = {}

    def get_aps(self, true, pred):
        num_classes = len(self.class_map.keys())
        dict_aps = {}
        for i in range(num_classes):
            ap = average_precision_score(true[:, i], pred[:, i])
            dict_aps[self.class_map[i]] = ap
        return dict_aps

    def on_epoch_end(self, epoch, logs=None):
        print("starting validation...")
        self.val_gen.reset()
        pred = self.model.predict(self.val_gen)
        true = self.val_gen.labels
        dict_aps = self.get_aps(true, pred)
        val_loss = tf.reduce_mean(self.model.loss(true, pred) + tf.reduce_sum(self.model.losses))
        mean_ap = np.mean(list(dict_aps.values()))
        # remember best model weights
        if mean_ap > self.best_mean_ap:
            self.best_mean_ap = mean_ap
            self.best_weights = self.model.get_weights()
            self.average_precision_per_class = dict_aps
        logs["val_loss"] = val_loss
        logs["mean_average_precision"] = mean_ap
        print("validation completed")

    def on_train_end(self, logs=None):
        timestamp = get_datetime_str(self._start_time)
        self.model.set_weights(self.best_weights)
        if self.save_model:
            print("saving model for tensorflow serving...")
            # save model for tf-serving. use "saved_model_cli show --dir {export_path} --all" to inspect signatures
            self.model.save(os.path.join(DOCKER_ATTACH_MODEL, timestamp, "1"),
                            save_format="tf", include_optimizer=False)
            with open(os.path.join(DOCKER_ATTACH_MODEL, timestamp, CLASS_MAP_FILE_NAME), 'w') as f:
                for i in range(len(self.class_map.keys())):
                    f.write("{}\n".format(self.class_map[i]))
            if os.path.islink(FILE_PATH_TFS_MODEL_DIR) or os.path.isfile(FILE_PATH_TFS_MODEL_DIR):
                os.remove(FILE_PATH_TFS_MODEL_DIR)
            os.symlink(os.path.join(".", timestamp), FILE_PATH_TFS_MODEL_DIR, True)
            self._update_pg_db()
            print("saving completed")

    # TODO: create failsafe section
    def _update_pg_db(self):
        postgres_con = create_postgres_connection()
        # noinspection PyProtectedMember
        postgres_cur: psycopg2._psycopg.cursor = postgres_con.cursor()

        # store new model in db
        start_datetime = datetime.fromtimestamp(self._start_time)
        postgres_cur.execute(
            """INSERT INTO model (date, dir_name, inference_stored)
            VALUES (%s, %s, %s) """,
            (start_datetime, get_datetime_str(self._start_time), False)
        )
        # query new model id
        postgres_con.commit()
        postgres_cur.execute(
            """SELECT id
             FROM model
             WHERE date = %s""",
            (start_datetime,)
        )
        model_id = postgres_cur.fetchone()[0]

        # insert precision per class for new model
        execute_values(postgres_cur,
                       "INSERT INTO evaluation (modelid, classid, precision) VALUES %s",
                       [(model_id, class_id, precision) for class_id, precision in
                        self.average_precision_per_class.items()])
        postgres_con.commit()

        postgres_cur.close()
        postgres_con.close()
