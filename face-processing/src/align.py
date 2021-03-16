import dlib
import cv2
from imutils.face_utils import FaceAligner
from config import PATH_SHAPE_PREDICTOR
from errors import *
import os


def init_aligner(path=PATH_SHAPE_PREDICTOR):
    predictor = dlib.shape_predictor(path)
    aligner = FaceAligner(predictor, desiredFaceWidth=160)
    return aligner


def align_faces(img, dets, aligner):
    imcrops = []
    try:
        for det in dets:
            x, y, w, h = list(det.split(" "))
            x = int(x)
            y = int(y)
            w = int(w)
            h = int(h)
            bbox = dlib.rectangle(left=x, top=y, right=x+w, bottom=y+h)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faceAligned = aligner.align(img, gray, bbox)
            imcrops.append(faceAligned)
    except:
        raise NoFaceInImageError()
    return imcrops


def align_faces_sim_search(img, dets, aligner):
    imcrops = []
    try:
        for det in dets:
            x, y, w, h = list(det)
            x = int(x)
            y = int(y)
            w = int(w)
            h = int(h)
            bbox = dlib.rectangle(left=x, top=y, right=x+w, bottom=y+h)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faceAligned = aligner.align(img, gray, bbox)
            imcrops.append(faceAligned)
    except:
        raise NoFaceInImageError()
    return imcrops


def get_aligned_face(img, dets):

    imcrops = []
    try:
        fa = init_aligner()
    except:
        raise AlignerNotFoundError()

    try:
        imcrops = align_faces(img, dets, fa)
    except:
        raise NoFaceInImageError()

    p,f = os.path.split(impath)
    facepath = os.path.join(p, "face_"+f)
    cv2.imwrite(facepath, imcrops[0])

    with open(facepath, 'rb') as f:
        face_img = f.read()

    return face_img
