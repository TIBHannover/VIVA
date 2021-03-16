import os
from datetime import datetime

CLASS_TYPE_CONCEPT = int(os.environ['DB_CLTP_ID_CONCEPT'])
CLASS_TYPE_PERSON = int(os.environ['DB_CLTP_ID_PERSON'])

DJANGO_APP_NAMES = [os.environ['DJANGO_APP_NAME_CONCEPT'], os.environ['DJANGO_APP_NAME_PERSON']]

GPU_MODE = int(os.environ['GPU_MODE']) == 1

# ### Training & Inference
# Training
TRAINING_LOG_STEP = int(os.environ['TRAINING_LOG_STEP'])
TRAINING_MAX_EPOCHS_2ND_PHASE = int(os.environ['TRAINING_MAX_EPOCHS_2ND_PHASE'])
TRAINING_MAX_EPOCHS_FIRST_PHASE = int(os.environ['TRAINING_MAX_EPOCHS_FIRST_PHASE'])
TRAINING_DELTA_STOP = float(os.environ['TRAINING_DELTA_STOP'])
TRAINING_DELTA_PATIENCE = int(os.environ['TRAINING_DELTA_PATIENCE'])

# Both
DEFAULT_TARGET_SIZE = (300, 300)  # 300 for EfficientNet
CLASS_MAP_FILE_NAME = "class_map.txt"

# ### REDIS KEYS
# HW Info
RKEY_HWINFO_GPU_NAME = os.environ["REDIS_KEY_GPU_NAMES"]
RKEY_HWINFO_GPU_UTIL = os.environ["REDIS_KEY_GPU_UTIL"]
RKEY_HWINFO_GPU_MEM_AVAIL = os.environ["REDIS_KEY_GPU_MEM_AVAIL"]
RKEY_HWINFO_GPU_MEM_USED = os.environ["REDIS_KEY_GPU_MEM_USED"]
RKEY_HWINFO_GPU_TEMP = os.environ["REDIS_KEY_GPU_TEMP"]


# S(erver) S(ide) E(vents)
SSE_TYPE_HW_INFO = "hw_info"
SSE_TYPE_TRAIN_INFO = "train_info"
SSE_TYPE_EPOCH_INFO = "epoch_info"


# ### Docker
# default attached paths
DOCKER_ATTACH_MEDIA = "/media"
DOCKER_ATTACH_LOGS = "/logs"
DOCKER_ATTACH_MODEL = "/models"

# file paths
FILE_PATH_TFS_MODEL_DIR = os.path.join(DOCKER_ATTACH_MODEL, os.environ["FILE_TFS_MODEL_DIR"])
FILE_PATH_LATEST_LOGS = os.path.join(DOCKER_ATTACH_LOGS, "latest")

# log files - always write to same file - copy if successful
FILE_NAME_LOG_TRAINING = "training.log"
FILE_NAME_LOG_INFERENCE = "inference.log"
FILE_PATH_LOG_TRAINING = os.path.join(FILE_PATH_LATEST_LOGS, FILE_NAME_LOG_TRAINING)
FILE_PATH_LOG_INFERENCE = os.path.join(FILE_PATH_LATEST_LOGS, FILE_NAME_LOG_INFERENCE)


# collections ids
DRA_KEYFRAMES_ID = 10

# TensorFlow Serving HTTP service URL
URL_TFS_START = os.environ["URL_TFS_START"]
URL_TFS_STOP = os.environ["URL_TFS_STOP"]


# Additional functions for consts
def get_datetime_str(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d_%H-%M-%S")
