from config import PATH_MODEL_FILE
from facenet.contributed.face import Encoder
import cv2


processed = 0


def get_embed_processed():
    global processed
    return processed


def increment_embed_processed():
    global processed
    processed += 1


def reset_embed_processed():
    global processed
    processed = 0


def get_face_embedding(img):
    embedding = None
    embedding = embed_face(img)
    return embedding

def get_multiple_embeddings(imcrops):
    embeddings = []
    try:
    # https://github.com/davidsandberg/facenet/issues/1112
    # Use pb file instead of meta and ckpt with tf2+
        encoder = Encoder(PATH_MODEL_FILE)
    except:
        raise ModelNotFoundError()
    for imcrop in imcrops:
        embeddings.append(embed_face(imcrop, encoder=encoder))
    return embeddings


def embed_face(img, encoder=None):
    if not encoder:
        try:
        # https://github.com/davidsandberg/facenet/issues/1112
        # Use pb file instead of meta and ckpt with tf2+
            encoder = Encoder(PATH_MODEL_FILE)
        except:
            raise ModelNotFoundError()

    face = encoder.resize_face(img)
    face_embedding = encoder.generate_embedding(face)
    return face_embedding
