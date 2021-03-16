# Config for face recognition service

PATH_LABELS_FILE = "/code/index/lbs_dra_facenet_512.csv"
PATH_INDEX_FILE= "/code/index/index_dra_facenet_512.index"
PATH_MODEL_FILE= "/code/models/vggface2/20180402-114759/20180402-114759.pb"
PATH_SHAPE_PREDICTOR = "/code/models/aligner/shape_predictor_68_face_landmarks.dat"
PATH_EXAMPLE_IMG= "/code/examples/bild.jpg"
PATH_EMBEDDING_FILE = "/code/models/embeddings/VIVA_facenet_512.hdf5"
PATH_EMBEDDING_LABEL_FILE = "/code/models/embeddings/labels_VIVA_facenet_512.csv"
PATH_TRAINING_EMBEDDING_FILE = "/code/models/training/VIVA_facenet_512.hdf5"
PATH_TRAINING_EMBEDDING_LABEL_FILE = "/code/models/training/labels_VIVA_facenet_512.csv"
PATH_CLASSIFIER = "/code/models/classifier/classifier-facenet-train-dra-feedback-web.pkl"
MODE="gpu"
DETECTOR_MODEL = "RetinaNetResNet50"