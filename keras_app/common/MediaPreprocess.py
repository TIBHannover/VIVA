from typing import List, Tuple

import psycopg2.extensions
from keras_preprocessing.image import DataFrameIterator
from pandas import DataFrame
from tensorflow import keras

from .consts import DEFAULT_TARGET_SIZE


def get_class_names(db_cursor: psycopg2.extensions.cursor) -> List[Tuple[int, str]]:
    db_cursor.execute(
        """SELECT id, name
        FROM class"""
    )
    return db_cursor.fetchall()


def get_train_classes(db_cursor: psycopg2.extensions.cursor, min_positive_imgs_per_class: int,
                      class_type: int) -> List[Tuple[int, int]]:
    db_cursor.execute(
        """SELECT classid, count(*)
        FROM imageannotation i
        JOIN class  c on i.classid = c.id
        WHERE i.difficult IS FALSE AND i.groundtruth is TRUE AND c.classtypeid=%s 
        GROUP BY classid
        HAVING count(*) >= %s
        ORDER BY classid""",
        (class_type, min_positive_imgs_per_class,)
    )
    return db_cursor.fetchall()


def get_annotations_for_class(db_cursor: psycopg2._psycopg.cursor, class_id: int, collectionid: int = None) -> List[
    tuple]:
    if collectionid is None:
        db_cursor.execute(
            """SELECT path, groundtruth, collectionid
            FROM imageannotation i
            JOIN image i2 on i.imageid = i2.id
            WHERE difficult IS FALSE
            AND i.classid = %s""",
            (class_id,)
        )
    else:
        db_cursor.execute(
            """SELECT path, groundtruth
            FROM imageannotation i
            JOIN image i2 on i.imageid = i2.id
            WHERE difficult IS FALSE
            AND i.classid = %s
            AND i2.collectionid= %s""",
            (class_id, collectionid)
        )
    return db_cursor.fetchall()


def get_generator(pd_data: DataFrame, db_class_ids, batch_size: int, for_test=False) -> DataFrameIterator:
    def f(np_img):
        # additional pre-processing ops if needed
        return np_img

    if not for_test:
        data_gen = keras.preprocessing.image.ImageDataGenerator(
            preprocessing_function=f,
            shear_range=0.05,
            zoom_range=0.05,
            horizontal_flip=False
        )
    else:
        data_gen = keras.preprocessing.image.ImageDataGenerator(
            preprocessing_function=f)
    return data_gen.flow_from_dataframe(
        dataframe=pd_data,
        x_col="id",
        y_col=list(db_class_ids),
        shuffle=False if for_test else True,
        class_mode="raw",
        target_size=DEFAULT_TARGET_SIZE,
        batch_size=batch_size,
        validate_filenames=False)
