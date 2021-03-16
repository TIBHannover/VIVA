import datetime
import os
import sys
import traceback
from typing import Tuple

import psycopg2.extensions

from common.SharedUtils import create_postgres_connection, create_redis_connection, set_export_stop
from common.SharedValues import SharedValues
from common.consts import CLASS_TYPE_CONCEPT, CLASS_TYPE_PERSON, get_datetime_str
from export.PredictionsExport import export_class_detections


def get_latest_prediction_model_data(cur: psycopg2.extensions.cursor,
                                     class_type_id: int) -> Tuple[int, datetime.datetime]:
    cur.execute(
        """SELECT modelid, date
        FROM model
        JOIN evaluation e on model.id = e.modelid
        JOIN class c on c.id = e.classid
        WHERE classtypeid = %s
        AND inference_stored = TRUE
        ORDER BY date DESC
        LIMIT 1""", (class_type_id,))
    latest_model = cur.fetchone()
    return latest_model


def start_export(sv_instance: SharedValues, app_name: str) -> None:
    if app_name == os.environ['DJANGO_APP_NAME_CONCEPT']:
        class_type_id = CLASS_TYPE_CONCEPT
    else:
        class_type_id = CLASS_TYPE_PERSON

    postgres_con = create_postgres_connection()
    postgres_cur = postgres_con.cursor()

    latest_model = get_latest_prediction_model_data(postgres_cur, class_type_id)
    redis_con = create_redis_connection()
    if not latest_model:
        set_export_stop(redis_con, sv_instance, app_name, exception="No predictions to export")
        redis_con.close()
        return

    options = {
        'app_name': app_name,
        'class_type_id': class_type_id,
        'threshold': int(redis_con.get(os.environ['REDIS_KEY_EXPORT_THRESHOLD'].format(app_name))),
        'model_id': latest_model[0],
        'model_date_str': get_datetime_str(int(latest_model[1].timestamp())),
        'time': int(redis_con.get(os.environ['REDIS_KEY_EXPORT_TIME'].format(app_name)))
    }
    redis_con.close()

    try:
        export_class_detections(options, postgres_cur, sv_instance, '/tmp/viva/', '/export/')
        export_exception = None
    except Exception as e:
        export_exception = str(e)
        print(repr(e), file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
    except KeyboardInterrupt:
        return

    postgres_cur.close()
    postgres_con.close()

    redis_con = create_redis_connection()
    redis_con.set(os.environ['REDIS_KEY_EXPORT_MODEL_IDENT'].format(app_name), options['model_date_str'])
    set_export_stop(redis_con, sv_instance, app_name, exception=export_exception)
    redis_con.close()
