import os
from copy import copy

import requests
import json
from base64 import b64encode

from django.core.exceptions import ObjectDoesNotExist

from base.models import Image, Bboxannotation, Imageurl
from face_recognition.face_detection.bboxannotation import set_image_bbox
from viva.settings import PersonTrainInferConfig


def update_groundtruth_annotation(serialized_images, classid, mode="bbox", bbox_lst=None):
    if bbox_lst is None:
        bbox_lst = []
    id_set = set()
    if 'elements' in serialized_images:
        idx = 0
        for element in serialized_images['elements']:
            element.update({
                'media_type': 'image'
            })
            # TODO fix this issue of duplicated detections in face_detection
            if 'id' in element:
                if element['id'] not in id_set:
                    id_set.add(element['id'])
                else:
                    serialized_images['elements'].remove(element)
                    idx -= 1
                    continue

                if bbox_lst:
                    element.update({
                        'bbox': bbox_lst[idx]
                    })

                if mode == 'bbox':
                    try:
                        Bboxannotation.objects.get(imageid__id=element['id'], classid_id=classid,
                                                   x=element['bbox']['x'],
                                                   y=element['bbox']['y'], w=element['bbox']['w'],
                                                   h=element['bbox']['h'])
                        anno_exists = True
                    except ObjectDoesNotExist:
                        anno_exists = False
                elif mode == 'image':
                    bbox_set = Bboxannotation.objects.filter(imageid__id=element['id'], classid_id=classid).all()
                    anno_exists = True if bbox_set else False

                if anno_exists:
                    element.update({
                        'annotation': {'groundtruth': True}
                    })

                idx += 1

    return serialized_images


def update_face_list_from_db(serialized_images, bboxes):
    """
    Update the given list of image dicts with the corresponding bounding box list
    :param serialized_images: list of image dicts
    :param bboxes: bboxannotation queryset
    :return:
    """
    for image in serialized_images:
        bbox_object = bboxes.filter(imageid__id=image['id']).all()
        image.update({
            'media_type': 'image'
        })

        if bbox_object:
            f_list = []
            for bbox in bbox_object:
                f_list.append({
                    'bbox': {'x': bbox.x,
                             'y': bbox.y,
                             'w': bbox.w,
                             'h': bbox.h}
                })
                image.update({
                    'bbox_list': f_list
                })

    new_images = []
    for image in serialized_images:
        if 'download_url' in image.keys():
            if 'path' in image.keys():
                del image['path']

        if 'bbox_list' in image.keys():
            for bbox in image['bbox_list']:
                new_image = copy(image)
                del new_image['bbox_list']
                new_image['bbox'] = bbox['bbox']
                new_images.append(new_image)
    return new_images


def update_face_list(images, is_web=False, is_inference=False, user=None):
    """
    Update and return the images with the added Bounding Boxes
    :param images: List of dictionaries of the images.
    :param is_web: Whether or not the images are from the web or the database.
    :param is_inference: Whether or not in inference mode
    :param user: the user
    :return: List of dictionaries of the images with the added Bounding Boxes.
    """
    if not images:
        return []
    bbox_check_list = []
    for image in images:
        if is_inference:
            bbox_check_list.append(False)
            continue
        try:
            if not is_web:
                db_image = Image.objects.get(id=image['id'])
                bbox_object = Bboxannotation.objects.filter(imageid=db_image)
            else:
                db_image = Imageurl.objects.get(url=image['download_url'])
                bbox_object = Bboxannotation.objects.filter(imageid=Image.objects.get(imageurl=db_image))
            image.update({
                'media_type': 'image'
            })
            if bbox_object:
                f_list = []
                for bbox in bbox_object:
                    f_list.append({
                        'bbox': {'x': bbox.x,
                                 'y': bbox.y,
                                 'w': bbox.w,
                                 'h': bbox.h}
                    })
                    image.update({
                        'bbox_list': f_list
                    })
                bbox_check_list.append(True)
            else:
                bbox_check_list.append(False)
        except:
            bbox_check_list.append(False)
    return detect_faces(images, bbox_check_list, is_web=is_web, set_abstract_bbox=is_inference, user=user)


def detect_faces(images, bbox_check_list, is_web, set_abstract_bbox, user):
    """
    Detect faces of the images. Requests to the face service get chunked
    :param images: All the images that should be processed.
    :param bbox_check_list: List of bools whether or not a detection should be executed. (True if bbox already exists)
    :param is_web: Whether or not the images are from the web or the database.
    :param set_abstract_bbox: Whether or not the bounding boxes should be written to the database
    :param user: the user
    :return:
    """
    image_request_list = []
    filetypes = []
    actual_images = []
    bbox_check_list_f = []
    if is_web:
        for idx, image in enumerate(images):
            if 'download_url' in image.keys():
                try:
                    content = requests.get(image['download_url']).content
                    if content:
                        img_enc = b64encode(content)
                        image_request_list.append(img_enc)
                        filetypes.append('jpg')
                        actual_images.append(image)
                        bbox_check_list_f.append(bbox_check_list[idx])
                except:
                    print('Error in loading image. Possibly not trusted source')
        bbox_check_list = bbox_check_list_f
    else:
        for image in images:
            if 'path' in image.keys():
                with open(image['path'], 'rb') as f:
                    img = f.read()
                img_enc = b64encode(img)
                image_request_list.append(img_enc)
                filetypes.append(os.path.splitext(image['path'])[1])
                actual_images.append(image)

    image_chunks = []
    image_request_chunks = []
    bboxes_chunks = []
    filetypes_chunks = []
    if len(image_request_list) == len(bbox_check_list):
        for i in range(0, len(image_request_list), PersonTrainInferConfig.CHUNK_SIZE):
            image_request_chunks.append(image_request_list[i:i + PersonTrainInferConfig.CHUNK_SIZE])
            bboxes_chunks.append(bbox_check_list[i:i + PersonTrainInferConfig.CHUNK_SIZE])
            filetypes_chunks.append(filetypes[i:i + PersonTrainInferConfig.CHUNK_SIZE])
            image_chunks.append(actual_images[i:i + PersonTrainInferConfig.CHUNK_SIZE])
    else:
        return None
    res = []
    reset = True
    for image_request_chunk, bboxes_chunk, filetypes_chunk, image_chunk in zip(image_request_chunks, bboxes_chunks,
                                                                               filetypes_chunks, image_chunks):
        if reset:
            body = {
                'images': image_request_chunk,
                'bboxes': bboxes_chunk,
                'filetypes': filetypes_chunk,
                'total_images': len(images)
            }
            reset = False
        else:
            body = {
                'images': image_request_chunk,
                'bboxes': bboxes_chunk,
                'filetypes': filetypes_chunk
            }
        response = requests.post(PersonTrainInferConfig.URL_ALIAS + '/detect_faces', body)

        code = response.status_code

        if not code == 200:
            return None, None

        response = json.loads(response.text)

        if 'faces' in response.keys() and 'errors' in response.keys():
            faces = response['faces']
            errors = response['errors']
            if len(image_chunk) != len(faces):
                return []
            for image, face, error in zip(image_chunk, faces, errors):
                if error == "":
                    f_list = []
                    for f in face:
                        x, y, w, h = f
                        if f not in f_list:
                            f_list.append({'bbox': {'x': x, 'y': y, 'w': w, 'h': h}})
                    image.update({
                        'bbox_list': f_list
                    })
            new_images = []
            for image in image_chunk:
                if 'bbox_list' in image.keys():
                    for bbox in image['bbox_list']:
                        new_image = copy(image)
                        del new_image['bbox_list']
                        new_image['bbox'] = bbox['bbox']
                        new_images.append(new_image)

            # TODO check if this is needed
            # # inference case for saving bbox annotations without class labels
            # if set_abstract_bbox:
            #     for image_dict in new_images:
            #         image = Image.objects.get(id=image_dict['id'])
            #         bbox_set = Bboxannotation.objects.filter(imageid=image, x=image_dict['bbox']['x'],
            #                                                  y=image_dict['bbox']['y'], w=image_dict['bbox']['w'],
            #                                                  h=image_dict['bbox']['h'])
            #         if not bbox_set.exists():
            #             set_image_bbox(image=image, class_id=None, bbox=image_dict['bbox'], user=user)

            res.extend(new_images)
    return res


def encode_img_bbox(image):
    img_enc, filetype = "", ""
    # case not downloaded web image
    if 'download_url' in image.keys():
        try:
            content = requests.get(image['download_url']).content
            if content:
                img_enc = b64encode(content)
                filetype = 'jpg'
        except:
            pass
    # case media folder
    elif 'path' in image.keys():
        with open(image['path'], 'rb') as f:
            img = f.read()
        img_enc = b64encode(img)
        filetype = os.path.splitext(image['path'])[1]

    bbox = str('' + str(image['bbox']['x']) + ' ' + str(image['bbox']['y']) + ' ' + str(
        image['bbox']['w']) + ' ' + str(image['bbox']['h']))

    return img_enc, filetype, bbox


def create_image_encodings(images, training):
    """
    Creates image encodings in the faiss_s service for all the given images. Requests to the face service get chunked
    :param training:
    :param images:
    :return:
    """

    image_chunk, det_chunk, filetype_chunk, id_chunk = [], [], [], []
    reset = True
    idx = 0

    for i, image in enumerate(images):
        try:
            img_enc, filetype, bbox = encode_img_bbox(image)
            if not img_enc:
                continue
            image_chunk.append(img_enc)
            filetype_chunk.append(filetype)
            det_chunk.append(bbox)

            if training:
                id_chunk.append(image['classid'])
            else:
                id_chunk.append(image['id'])
        except:
            continue

        idx += 1

        if idx % PersonTrainInferConfig.CHUNK_SIZE == 0 or i == len(images) - 1:

            if reset:
                body = {
                    'images': image_chunk,
                    'dets_list': det_chunk,
                    'filetypes': filetype_chunk,
                    'image_names': id_chunk,
                    'training': training,
                    'total_images': len(images)
                }
                reset = False
            else:
                body = {
                    'images': image_chunk,
                    'dets_list': det_chunk,
                    'filetypes': filetype_chunk,
                    'image_names': id_chunk,
                    'training': training
                }

            requests.post(PersonTrainInferConfig.URL_ALIAS + '/create_image_encodings', body)
            image_chunk, det_chunk, filetype_chunk, id_chunk = [], [], [], []


def reset_counters():
    requests.post(PersonTrainInferConfig.URL_ALIAS + '/reset_counters')
