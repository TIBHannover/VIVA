import base64
import csv
import io
import logging
import os

import cv2
import h5py
import hug
import numpy as np
from PIL import Image
from falcon import HTTPBadRequest, HTTPNotImplemented
from hug.middleware import CORSMiddleware, LogMiddleware

from align import get_aligned_face, align_faces, init_aligner
from config import PATH_EMBEDDING_FILE, PATH_MODEL_FILE, PATH_EMBEDDING_LABEL_FILE, PATH_TRAINING_EMBEDDING_FILE, \
    PATH_TRAINING_EMBEDDING_LABEL_FILE
from detection import get_faces, get_multiple_faces, get_detection_processed, reset_detection_processed
from encoder import get_face_embedding, get_embed_processed, embed_face, increment_embed_processed, \
    reset_embed_processed
from errors import *
from facenet.contributed.face import Encoder
from similarity_search import get_similar_faces

detection_total = 0
embed_total = 0


if os.getenv("HUG_DEBUG", "0") == "1":
    class CustomLogMiddleware(LogMiddleware):
        def process_request(self, request, response):
            pass

    api = hug.API(__name__)
    api.http.add_middleware(CORSMiddleware(api, allow_origins=["http://localhost:" + os.getenv("PORT_DJANGO", "8000"),
                                                               "http://127.0.0.1:" + os.getenv("PORT_DJANGO", "8000")]))
    api.http.add_middleware(CustomLogMiddleware())
    logging.basicConfig(level=logging.INFO)


def stringToRGB(img_string):
    imgdata = base64.b64decode(str(img_string))
    image = Image.open(io.BytesIO(imgdata))
    return cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)


@hug.get("/info")
def info():
    return {'detection_total': detection_total, 'detection_processed': get_detection_processed(), 
            'embed_total': embed_total, 'embed_processed': get_embed_processed()}
    

@hug.post("/reset_counters")
def reset():
    global detection_total
    global embed_total
    detection_total = 0
    embed_total = 0
    reset_embed_processed()
    reset_detection_processed()


@hug.post("/detect_face")
def do_face_detect(body):
    required = ('img', 'filetype')
    if not all([r in body.keys() for r in required]):
        raise HTTPBadRequest(description="Required:" + ", ".join(required))
    error = ""
    dets = []
    try:
        try:
            img = stringToRGB(body['img'])
        except:
            raise CouldNotReadFileError()
        
        dets = get_faces(img)
    except CouldNotReadFileError:
        error = "File could not be read"
    except DetectorNotFoundError:
        error = "Face Detector could not be loaded"
    except NoFaceInImageError:
        error = "Found no face in image"

    return {'faces': dets, 'error': error}


@hug.post("/detect_faces")
def do_face_detect_multiple(body):
    required = ('images', 'bboxes', 'filetypes')
    if not all([r in body.keys() for r in required]):
        raise HTTPBadRequest(description="Required:" + ", ".join(required))
    images = body['images']
    bboxes = body['bboxes']
    img_lst = []
    
    if not (len(images) == len(bboxes) or len(images) == len(body['filetypes'])):
        raise HTTPBadRequest(description="Lists do not have the same lengths")

    global detection_total
    if 'total_images' in body.keys():
        detection_total = int(body['total_images'])
    
    if type(images) == str:
        images = [images]
    if type(bboxes) == str:
        bboxes = [bboxes]
    for id, (image, bbox, filetype) in enumerate(zip(images, bboxes, body['filetypes'])):
        if bbox == True:
            img_lst.append('')
        else:
            try:
                img_lst.append(stringToRGB(image))
            except:
                raise CouldNotReadFileError()
    dets, errors = get_multiple_faces(img_lst, bboxes)
    return {'faces': dets, 'errors': errors}


@hug.post("/align_face")
def do_face_align(body):
    required = ('img', 'filetype', 'dets')
    if not all([r in body.keys() for r in required]):
        raise HTTPBadRequest(description="Required:" + ", ".join(required))

    error = ""
    imcrop = ""
    try:

        try:
            img = stringToRGB(body['img'])
        except:
            raise CouldNotReadFileError()
        
        dets = body['dets']

        try:
            if not isinstance(dets[0], list):
                dets = [dets]
            int_dets = []
            for x, y, w, h in dets:
                int_dets.append((int(x), int(y), int(w), int(h)))
        except:
            raise HTTPBadRequest()

        
        face_img = get_aligned_face(img, int_dets)
        imcrop = base64.b64encode(face_img)

    except CouldNotReadFileError:
        error = "File could not be read"
    except AlignerNotFoundError:
        error = "Face aligner could not be loaded"
    except NoFaceInImageError:
        error = "Found no face in image"

    return {'face': imcrop, 'error': error}


@hug.post("/embed_face")
def do_face_embed(body):
    required = ('img', 'filetype')
    if not all([r in body.keys() for r in required]):
        raise HTTPBadRequest(description="Required:" + ", ".join(required))
    error = ""
    embedding = ""
    try:
        try:
            img = stringToRGB(body['img'])
        except:
            raise CouldNotReadFileError()
        
        embedding = get_face_embedding(img)
    except CouldNotReadFileError:
        error = "File could not be read"
    except ModelNotFoundError:
        error = "Face Encoder could not be loaded"

    return {'embedding': embedding, 'error': error}


@hug.post("/train_faces")
def do_face_training(body):
    raise HTTPNotImplemented()


@hug.post('/similarity_search')
def do_similarity_search(body):
    required = ('img', 'filetype')
    if not all([r in body.keys() for r in required]):
        raise HTTPBadRequest(description="Required:" + ", ".join(required))
    
    paths, error = [], ""

    try:
        try:
            img = stringToRGB(body['img'])
        except:
            raise CouldNotReadFileError()

        paths = get_similar_faces(img, int(body['max_results']), body['query_bbox'])
    
    except CouldNotReadFileError:
        error = "File could not be read"
    except ModelNotFoundError:
        error = "No pre-trained model could be found"
    except AlignerNotFoundError:
        error = "No face aligner could be found"
    except DetectorNotFoundError:
        error = "No face detector could be found"
    except IndexNotFoundError:
        error = "No faiss index could be found"    
    except NoFaceInImageError:
        error = "No face found in image"
    except NotAlignedError:
        error = "Faces could not be aligned"
    
    result = {
        "paths": paths,
        "error": error
    }
    return result


@hug.post("/create_image_encodings")
def create_image_encodings(body):
    required = ('images', 'dets_list', 'filetypes', 'image_names', 'training')
    if not all([r in body.keys() for r in required]):
        raise HTTPBadRequest(description="Required:" + ", ".join(required))
    images = body['images']
    dets_list = body['dets_list']
    image_names = body['image_names']
    training = body['training']
    img_lst = []
    global embed_total

    if training == 'True':
        embedding_file = PATH_TRAINING_EMBEDDING_FILE
        embedding_label_file = PATH_TRAINING_EMBEDDING_LABEL_FILE
    else:
        embedding_file = PATH_EMBEDDING_FILE
        embedding_label_file = PATH_EMBEDDING_LABEL_FILE
    
    if 'total_images' in body.keys():
        embed_total = int(body['total_images'])
        if os.path.exists(embedding_file):
            os.remove(embedding_file)
        if os.path.exists(embedding_label_file):
            os.remove(embedding_label_file)
        h5_file = h5py.File(embedding_file, "a")
        features = h5_file.create_dataset('encodings', shape=(0, 512), dtype='float32', maxshape=(None, 512))
    else:
        features = load_h5py_dataset(training)

    if type(images) == str:
        images = [images]
    for id, (image, filetype) in enumerate(zip(images, body['filetypes'])):
        try:
            img_lst.append(stringToRGB(image))
        except:
            img_lst.append('')
            raise CouldNotReadFileError()
    try:
        fa = init_aligner()
    except:
        raise AlignerNotFoundError()
    try:
    # https://github.com/davidsandberg/facenet/issues/1112
    # Use pb file instead of meta and ckpt with tf2+
        encoder = Encoder(PATH_MODEL_FILE)
    except:
        raise ModelNotFoundError()
    
    with open(embedding_label_file, 'a') as f:
        writer = csv.writer(f)
        errors = []
        face_count = features.shape[0]
        for img, image_name, dets in zip(img_lst, image_names, dets_list):
            if img is None:
                continue
            error = ''
            dets = list(dets.split(","))
            try:
                imcrops = align_faces(img, dets, fa)
                
                for i, imcrop in enumerate(imcrops):
                    try:
                        embedding = embed_face(imcrop, encoder=encoder)
                        features.resize(features.shape[0] + 1, axis=0)
                        features[face_count,:] = embedding.astype('float32')
                        (x, y, w, h) = dets[i].split(" ")
                        writer.writerow([image_name, x, y, w, h])
                        face_count += 1
                    except:
                        error = "Face crop " + str(i) + " of " + impath + " could not be embedded."
            except CouldNotReadFileError:
                error = "File could not be read."
            except NoFaceInImageError:
                error = "No Face in Image."
            errors.append(error)
            increment_embed_processed()
    if 'total_images' in body.keys():
        h5_file.flush()
        h5_file.close()


def load_h5py_dataset(training):
    if training == 'True':
        features_file = h5py.File(PATH_TRAINING_EMBEDDING_FILE, 'a')
        dataset = features_file['encodings']
    else:
        features_file = h5py.File(PATH_EMBEDDING_FILE, 'a')
        dataset = features_file['encodings']
    return dataset


def get_label_list(training):
    if training == 'True':
        with open(PATH_TRAINING_EMBEDDING_LABEL_FILE, "r") as f:
            reader = csv.reader(f)
            labels = [(x[0], int(x[1]), int(x[2]), int(x[3]), int(x[4]))  for x in reader]
            return labels
    else:
        with open(PATH_EMBEDDING_LABEL_FILE, "r") as f:
            reader = csv.reader(f)
            labels = [(x[0], int(x[1]), int(x[2]), int(x[3]), int(x[4]))  for x in reader]
            return labels
