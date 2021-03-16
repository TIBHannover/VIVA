import cv2
import dlib
import face_detection
from errors import *
from config import DETECTOR_MODEL


processed = 0

def get_detection_processed():
    global processed
    return processed

def reset_detection_processed():
    global processed
    processed = 0


def convert_coords(det):
    x, y = det[0], det[1]
    w = det[2] - x
    h = det[3] - y
    return (x, y, w, h)


def trim_black_edges(det, imshape, margin_h=15, margin_w=25):
    x = max(margin_w, det[0])
    y = max(margin_h, det[1])
    w = min(imshape[1]-margin_w, det[2])
    h = min(imshape[0]-margin_h, det[3])
    return (int(x), int(y), int(w), int(h))


def allowed_aspect_ratio(w, h, t0=0.55, t1=1.1):
    ratio = w/h
    return ratio > t0 and ratio < t1


def allowed_height(h, t=80):
    return h > t


def allowed_blur(blur, t=10.0):
    return blur >= t


def variance_of_laplacian(img, dim=(160, 160)):
    # compute the Laplacian of the image and then return the focus
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.resize(gray, dim)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def detect_faces(img, detector):
    bboxes = []
    dets = detector.detect(
        img[:, :, ::-1]
    )[:, :4]
    for det in dets:
        det = convert_coords(det)
        x, y, w, h = trim_black_edges(det, img.shape)
        if not allowed_height(h):
            continue
        if not allowed_aspect_ratio(w, h):
            continue
        blur = variance_of_laplacian(img[y:y+h, x:x+w])
        if not allowed_blur(blur):
            continue
        bboxes.append((x, y, w, h))
    return bboxes


def init_detector(model=DETECTOR_MODEL):
    detector = face_detection.build_detector(
        model,
        confidence_threshold=.99,
        max_resolution=1080
    )
    return detector


def get_faces(img):
    dets = []
    try:
        detector = init_detector()
    except:
        raise DetectorNotFoundError()

    dets = detect_faces(img, detector)
    if len(dets) == 0:
        raise NoFaceInImageError()

    return dets


def get_multiple_faces(images, bboxes):
    errors = []
    mult_dets = []
    try:
        detector = init_detector()
    except:
        raise DetectorNotFoundError()
    global processed
    for img, bbox in zip(images, bboxes):
        error = ""
        if bbox == "False":
            if img is not None:
                dets = detect_faces(img, detector)
                if len(dets) == 0:
                    mult_dets.append([[]])
                    error = "No face in image"
                else:
                    mult_dets.append(dets)
            else:
                mult_dets.append([[]])
                error = "Image is None"
        else:
            mult_dets.append([[]])
            error = "Bounding box already in Database"
        errors.append(error)
        processed += 1
    
    return mult_dets, errors
