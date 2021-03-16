from random import shuffle
from typing import List, Dict

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras

from common.MediaPreprocess import get_annotations_for_class, get_train_classes, get_generator
from common.SharedUtils import create_postgres_connection, create_redis_connection, sse_send_training_data
from common.SharedValues import SharedValues
from common.consts import *
from training.losses import focal_crossentropy
from training.EvaluationCallback import EvaluationCallback
from training.RedisSSECallback import RedisSSECallback
from training.LogCallback import NBatchLogger


class InsufficientTrainingData(Exception):
    pass


def create_pd_frame(dic, db_class_ids: List[str], is_val=False):
    # id is the path to image
    data_frame = {"id": list(dic.keys())}
    for db_class_id in db_class_ids:
        data_frame[db_class_id] = []
    for image_path in data_frame["id"]:
        label_gt_list = dict(dic[image_path])
        second_label = 0. if all(label_gt_list.values()) else -1.
        if is_val:
            second_label = 0.
        for db_class_id in db_class_ids:
            if db_class_id in label_gt_list.keys():
                data_frame[db_class_id].append(1. if label_gt_list[db_class_id] else 0.)
            else:
                data_frame[db_class_id].append(second_label)
    df = pd.DataFrame(data_frame, columns=['id'] + db_class_ids)
    return df


def multi_label_stratify(data, db_class_ids: List[str], class_counts: Dict[str, dict]):
    test_num_pos = int(os.environ['TRAINING_TEST_NUMBER_POSITIVE'])
    test_ratio_neg = float(os.environ['TRAINING_TEST_NEGATIVE_RATIO'])

    dra_keyframes = {k: v['y'] for k, v in data.items() if v['collection'] == DRA_KEYFRAMES_ID}
    rest = {k: v['y'] for k, v in data.items() if v['collection'] != DRA_KEYFRAMES_ID}

    train = {}
    val = {}
    pos_trackers = {db_class_id: test_num_pos for db_class_id in db_class_ids}
    neg_trackers = {db_class_id: np.ceil(class_counts[db_class_id]["neg"] * test_ratio_neg) for db_class_id
                    in db_class_ids}

    for dic in [dra_keyframes, rest]:
        t, v = sample(dic, pos_trackers, neg_trackers)
        train.update(t)
        val.update(v)
    return train, val


def sample(data, pos_trackers, neg_trackers):
    train = []
    val = []
    data_list = [(path, y) for path, y in data.items()]
    shuffle(data_list)
    for path, y in data_list:
        to_val = False
        for item in y:
            db_class_id, is_gt = item
            if is_gt and pos_trackers[db_class_id] > 0:
                val.append((path, y))
                to_val = True
                break
            if not is_gt and neg_trackers[db_class_id] > 0:
                val.append((path, y))
                to_val = True
                break
        if to_val:
            for item in y:
                db_class_id, is_gt = item
                pos_trackers[db_class_id] -= 1 if is_gt else 0
                neg_trackers[db_class_id] -= 1 if not is_gt else 0
        else:
            train.append((path, y))
    return {k: v for k, v in train}, {k: v for k, v in val}


def get_model_compiled(num_classes, lr):
    inputs = tf.keras.Input(shape=DEFAULT_TARGET_SIZE + (3,))

    backbone = tf.keras.applications.EfficientNetB3(
        include_top=False,
        weights="imagenet",
        input_tensor=inputs,
        input_shape=DEFAULT_TARGET_SIZE + (3,),
        pooling=None,
    )

    # Freeze the pretrained weights
    backbone.trainable = False

    x = backbone.output
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(0.2, name="top_dropout")(x)
    output = tf.keras.layers.Dense(num_classes, activation="sigmoid", name='predictions')(x)
    model = tf.keras.Model(inputs=backbone.input, outputs=output)
    optimizer = tf.keras.optimizers.Adam(learning_rate=lr)
    model.compile(
        optimizer=optimizer, loss=lambda y_true, y_pred: focal_crossentropy(y_true, y_pred, alpha=0.8))
    return model


def parse_class_annotations(data, db_class_id, results):
    for i, result in enumerate(results):
        filename, gt, collection_id = result
        image_path = os.path.join(DOCKER_ATTACH_MEDIA, filename)
        if image_path in data:
            data[image_path]['y'].append((db_class_id, gt))
            continue
        data[image_path] = {'y': [(db_class_id, gt)], 'collection': collection_id}


def train_viva_net(options: dict, sv_instance: SharedValues):
    postgres_con = create_postgres_connection()
    postgres_cur = postgres_con.cursor()

    db_class_ids = list(map(lambda c: str(c[0]),
                            get_train_classes(postgres_cur, int(os.environ["TRAIN_MIN_ANNO_PER_CLASS"]),
                                              class_type=CLASS_TYPE_CONCEPT)))
    if not db_class_ids:
        raise InsufficientTrainingData(
            "not enough data with {} as minimum number of positive samples per concept".format(
                os.environ["TRAIN_MIN_ANNO_PER_CLASS"]))

    num_classes = len(db_class_ids)
    data = {}
    class_counts = {}

    for db_class_id in db_class_ids:
        class_results = list(get_annotations_for_class(postgres_cur, int(db_class_id)))
        class_counts[db_class_id] = {"neg": len([1 for res in class_results if not res[1]])}
        parse_class_annotations(data, db_class_id, class_results)

    train, val = multi_label_stratify(data, db_class_ids, class_counts)

    # create pandas data frames
    pd_train = create_pd_frame(train, db_class_ids)
    pd_val = create_pd_frame(val, db_class_ids, is_val=True)

    # get generators
    train_gen = get_generator(pd_train, db_class_ids, options['batch_size'])
    val_gen = get_generator(pd_val, db_class_ids, options['batch_size'], for_test=True)

    tf.config.experimental.set_memory_growth = True
    strategy = tf.distribute.MirroredStrategy()
    with strategy.scope():
        train_net = get_model_compiled(num_classes, float(os.environ['TRAINING_LR_INIT']))
    gen_class_map = {i: int(db_class_id) for i, db_class_id in enumerate(db_class_ids)}

    # close db connection
    postgres_cur.close()
    postgres_con.close()

    redis_con = create_redis_connection()
    redis_con.set(os.environ['REDIS_KEY_TRAINING_TOTAL'], len(train_gen) *
                  (TRAINING_MAX_EPOCHS_FIRST_PHASE + TRAINING_MAX_EPOCHS_2ND_PHASE))
    redis_con.set(os.environ['REDIS_KEY_TRAINING_CURRENT'], 0)
    redis_con.set(os.environ['REDIS_KEY_TRAINING_STEPS_PER_EPOCH'], len(train_gen))
    redis_con.set(os.environ['REDIS_KEY_TRAINING_TIME_ETE'], int(datetime.timestamp(datetime.now())))
    sse_send_training_data(sv_instance, redis_con)
    redis_con.close()

    # callbacks
    eval_callback = EvaluationCallback(val_gen, gen_class_map, options['start_time'], save_model=False)
    reduce_lr = keras.callbacks.ReduceLROnPlateau(monitor='val_loss',
                                                  factor=float(os.environ['TRAINING_LR_REDUCE_FACTOR']),
                                                  patience=int(os.environ['TRAINING_LR_REDUCE_PATIENCE']),
                                                  min_lr=0.000001)
    stop_callback = keras.callbacks.EarlyStopping(monitor="mean_average_precision", mode="max",
                                                  min_delta=TRAINING_DELTA_STOP,
                                                  patience=TRAINING_DELTA_PATIENCE, verbose=1)
    epoch_callback = RedisSSECallback(sv_instance, len(train_gen))
    logger = NBatchLogger(TRAINING_LOG_STEP)

    print("First phase is running...")
    train_net.fit(train_gen,
                  epochs=TRAINING_MAX_EPOCHS_FIRST_PHASE,
                  workers=int(os.environ['TRAINING_WORKER_COUNT']),
                  callbacks=[eval_callback, logger, reduce_lr, epoch_callback, stop_callback],
                  use_multiprocessing=False,
                  max_queue_size=200,
                  verbose=0,
                  )

    def unfreeze_model(model):
        for layer in model.layers[-20:]:
            if not isinstance(layer, tf.keras.layers.BatchNormalization):
                layer.trainable = True

        optimizer = tf.keras.optimizers.Adam(learning_rate=float(os.environ['TRAINING_LR_INIT']) * 0.1)
        model.compile(
            optimizer=optimizer, loss=lambda y_true, y_pred: focal_crossentropy(y_true, y_pred, alpha=0.8)
        )

    unfreeze_model(train_net)
    eval_callback = EvaluationCallback(val_gen, gen_class_map, options['start_time'], save_model=True)

    print("Second phase is running...")
    train_net.fit(train_gen,
                  epochs=TRAINING_MAX_EPOCHS_2ND_PHASE,
                  workers=int(os.environ['TRAINING_WORKER_COUNT']),
                  callbacks=[eval_callback, logger, reduce_lr, epoch_callback, stop_callback],
                  use_multiprocessing=False,
                  max_queue_size=200,
                  verbose=0,
                  )
