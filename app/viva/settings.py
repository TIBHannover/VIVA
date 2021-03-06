"""
Django settings for viva project.

Generated by 'django-admin startproject' using Django 2.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import re
from pathlib import Path

import redis
from django.conf import global_settings
from django.urls import reverse_lazy

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# TODO: Change SECRET_KEY before publication
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'g!qaqblwhgs5(^71ob$0p9by1-osc$9j454nndk#$%y=t^d_j*')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = int(os.environ.get('DEBUG', default=0))

ALLOWED_HOSTS = ["*"]

# Set the number of GET/POST parameters allowed
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10100

# Set NGINX parameters according to nginx.conf
UPLOAD_LIMIT = int(os.environ.get('NGINX_UPLOAD_LIMIT', 1))  # in MiB

# Application definition

INSTALLED_APPS = [
    'menu',
    'base.apps.BaseConfig',
    'accounts.apps.AccountsConfig',
    'concept_classification.apps.ConceptClassificationConfig',
    'face_recognition.apps.FaceRecognitionConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_jinja',
    'django_rq'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'viva.middleware.AccessControlMiddleware'
]

if not DEBUG:
    INSTALLED_APPS += ['defender']
    MIDDLEWARE += ['defender.middleware.FailedLoginMiddleware']

ROOT_URLCONF = 'viva.urls'

TEMPLATES = [
    {
        "BACKEND": "django_jinja.backend.Jinja2",
        "APP_DIRS": True,
        "OPTIONS": {
            "match_extension": ".html",
            "environment": "viva.jinja2.environment",
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages"
            ]
        }
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages'
            ],
        },
    },
]

TEMPLATE_CONTEXT_PROCESSORS = ["django.template.context_processors.request"]
WSGI_APPLICATION = 'viva.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('SERVICE_DATABASE_POSTGRES'),
        'PORT': '5432',
    }
}
# Please set the collection IDs accordingly to your DB
# TODO check if these are still needed
DB_CRAWLER_COLLECTION_ID = 1
DRA_KEYFRAMES_COLLECTION_ID = 10

RQ_QUEUES = {
    'image_downloader': {
        'HOST': os.environ.get('SERVICE_DATABASE_REDIS'),
        'PORT': '6379',
        'DB': os.environ.get('REDIS_DB_QUEUE_WORKER'),
        # 'PASSWORD': 'some-password',
        # 'DEFAULT_TIMEOUT': 360,
    }
}

if DEBUG:
    import logging

    log = logging.getLogger('django.db.backends')
    log.setLevel(logging.DEBUG)
    log.addHandler(logging.StreamHandler())

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "rq_console": {
                "format": "%(asctime)s %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "rq_console": {
                "level": "DEBUG",
                "class": "rq.utils.ColorizingStreamHandler",
                "formatter": "rq_console",
                "exclude": ["%(asctime)s"],
            }, 'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            "rq.worker": {
                "handlers": ["rq_console"],
                "level": "DEBUG"
            },
            # 'django.db.backends': {
            #   'level': 'DEBUG',
            #   'handlers': ['console'],
            # },
        }
    }

# Only applies if server not in DEBUG-mode
DEFENDER_BEHIND_REVERSE_PROXY = True
DEFENDER_REVERSE_PROXY_HEADER = "HTTP_X_FORWARDED_FOR"
DEFENDER_DISABLE_IP_LOCKOUT = False
DEFENDER_DISABLE_USERNAME_LOCKOUT = True
DEFENDER_COOLOFF_TIME = 300
DEFENDER_LOCKOUT_URL = reverse_lazy("accounts:blocked")
DEFENDER_REDIS_URL = 'redis://redis:6379/' + os.environ.get('REDIS_DB_DEFENDER')

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SESSION_SAVE_EVERY_REQUEST = True
if not DEBUG:
    SESSION_COOKIE_AGE = 1800  # 30 minutes
    SESSION_COOKIE_SECURE = True
else:
    SESSION_COOKIE_AGE = global_settings.SESSION_COOKIE_AGE  # set default otherwise cannot be imported in jinja2.py

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = '/media'

VERSION_INFO_FILE_PATH = "base/static/version.info"
if DEBUG and os.path.isfile(VERSION_INFO_FILE_PATH):
    os.remove(VERSION_INFO_FILE_PATH)
ANNOUNCEMENTS_FILE_PATH = "/transfer/announcements.json"


class EsConfig:
    # Web App settings
    WS_DEBUG = True
    WS_ALLOWED_EXT = ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "tif"]
    WS_IMAGES_URL = "https://pc12439.mathematik.uni-marburg.de:8283/Annotation-Tool/MediaDbData/dradb/keyframes/images/"
    WS_THUMBS_URL = "https://pc12439.mathematik.uni-marburg.de:8283/Annotation-Tool/MediaDbData/dradb/keyframes/images/"

    # Elastic Search settings
    ES_MAX_RESULTS = 2000
    ES_URL = "http://" + os.environ.get('SERVICE_ELASTIC_SEARCH') + ":9200/es-retrieval/_search?size="

    # Hashcode webservice
    HC_URL = os.environ.get("HC_URL", "https://pc12439.mathematik.uni-marburg.de/dh/0.3/code")
    HC_CLIENT_HEADER = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/39.0.2171.95 Safari/537.36'}

    with open('concept_classification/similarity_search/el_query.json', 'r') as file:
        EL_QUERY_TPL = file.read()


class SessionConfig:
    SELECTED_CONCEPT_SESSION_KEY = "selected_concept"
    SELECTED_PERSON_SESSION_KEY = "selected_person"


class PersonTrainInferConfig:
    URL = "http://localhost:8001" if DEBUG else os.environ['URL_INTERNAL_HUG']  # use in javascript
    URL_ALIAS = "http://face-processing:8001"  # use in python
    FACE_MODELS_BASE_PATH = '/person_models'
    PATH_EMBEDDING_LABEL_FILE = FACE_MODELS_BASE_PATH + '/embeddings/labels_VIVA_facenet_512.csv'
    PATH_EMBEDDING_FILE = FACE_MODELS_BASE_PATH + '/embeddings/VIVA_facenet_512.hdf5'
    PREPATH_CLASSIFIER = FACE_MODELS_BASE_PATH + '/classifier/'
    PATH_TRAINING_EMBEDDING_LABEL_FILE = FACE_MODELS_BASE_PATH + '/training/labels_VIVA_facenet_512.csv'
    PATH_TRAINING_EMBEDDING_FILE = FACE_MODELS_BASE_PATH + '/training/VIVA_facenet_512.hdf5'
    LAST_N_MODELS_TO_KEEP = 4
    MIN_ANNOTATIONS = 30
    CHUNK_SIZE = 50  # chunk size for processing requests on the face-processing service


class KerasFlaskConfig:
    class Flask:
        URL = "http://localhost:8080" if DEBUG else os.environ['URL_INTERNAL_FLASK']
        URL_INTERNAL = "http://{:s}:8080".format(os.environ['SERVICE_KERAS_APP'])
        URL_SSE = os.environ['FLASK_URL_SSE']

        class Training:
            URL_START = os.environ['FLASK_URL_TRAINING_START']
            URL_STOP = os.environ['FLASK_URL_TRAINING_STOP']
            URL_UPDATE = os.environ['FLASK_URL_TRAINING_UPDATE']
            URL_LOG = os.environ['FLASK_URL_TRAINING_LOG']

        class Inference:
            URL_START = os.environ['FLASK_URL_INFERENCE_START']
            URL_STOP = os.environ['FLASK_URL_INFERENCE_STOP']
            URL_UPDATE = os.environ['FLASK_URL_INFERENCE_UPDATE']
            URL_LOG = os.environ['FLASK_URL_INFERENCE_LOG']

        class Export:
            URL_START = os.environ['FLASK_URL_EXPORT_START']
            URL_STOP = os.environ['FLASK_URL_EXPORT_STOP']
            URL_UPDATE = os.environ['FLASK_URL_EXPORT_UPDATE']

        class Sse:
            TYPE_TRAINING_INFO = os.environ['FLASK_SSE_TRAINING_INFO']
            TYPE_TRAINING_LOG = os.environ['FLASK_SSE_TRAINING_LOG']
            TYPE_INFERENCE_INFO = os.environ['FLASK_SSE_INFERENCE_INFO']
            TYPE_INFERENCE_LOG = os.environ['FLASK_SSE_INFERENCE_LOG']
            TYPE_EXPORT_INFO = os.environ['FLASK_SSE_EXPORT_INFO']
            KEY_LOG_MESSAGE = os.environ['FLASK_SSE_KEY_LOG_MESSAGE']
            KEY_LOG_CLEAR = os.environ['FLASK_SSE_KEY_LOG_CLEAR']

    class Training:
        MIN_ANNOTATIONS = int(os.environ['TRAIN_MIN_ANNO_PER_CLASS'])

    INFERENCE_THRESHOLD_DB_WRITE = float(os.environ['INFERENCE_THRESHOLD_DB_WRITE'])

    redis_connection_pool = redis.ConnectionPool(
        host=os.environ['SERVICE_DATABASE_REDIS'],
        port=6379,
        db=os.environ['REDIS_DB_TRAIN'],
        decode_responses=True)


class GridConfig:
    PARAMETER_PAGE = "page"
    PARAMETER_ELEMENT_COUNT = "element_count"
    PARAMETER_ANNOTATION_CLASS = "annotation_class"
    ELEMENT_ADDITIONAL_VALUE_SCORE = "score"


class AsyncActionConfig:
    KEY_RUN = os.environ['ASYNC_ACTION_KEY_RUN']
    KEY_DEPENDENCY_RUN = os.environ['ASYNC_ACTION_KEY_DEPENDENCY_RUN']
    KEY_DEPENDENCY_PREREQUISITE = os.environ['ASYNC_ACTION_KEY_DEPENDENCY_PRE']
    KEY_OPTIONS = os.environ['ASYNC_ACTION_KEY_OPTIONS']
    KEY_TIME = os.environ['ASYNC_ACTION_KEY_TIME']
    KEY_TIME_ETE = os.environ['ASYNC_ACTION_KEY_TIME_ETE']
    KEY_EXCEPTION = os.environ['ASYNC_ACTION_KEY_EXCEPTION']
    KEY_CURRENT = os.environ['ASYNC_ACTION_KEY_CURRENT']
    KEY_TOTAL = os.environ['ASYNC_ACTION_KEY_TOTAL']
