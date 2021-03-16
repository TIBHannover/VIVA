import json
import os
from statistics import mean
from typing import Callable

import redis
from django.core.exceptions import ObjectDoesNotExist
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest, Http404
from django.http.response import HttpResponseBase
from django.shortcuts import render
from django.utils.datastructures import MultiValueDictKeyError

from base.models import Class, Classtype, Image, Imageprediction, Video, Videoframe, Evaluation, Model, serialize_images
from base.tools.dataimport import allowed_file, read_csv
from base.tools.imageannotation import create_new_web_image, delete_image_annotation, set_image_annotation
from base.tools.webimagedownloader import add_image_to_download_queue
from concept_classification.apps import ConceptClassificationConfig
from face_recognition.apps import FaceRecognitionConfig
from face_recognition.face_detection.face_detection import update_face_list, update_groundtruth_annotation
from face_recognition.views import add_absolute_image_path
from viva.settings import SessionConfig, GridConfig, KerasFlaskConfig


def save_grid_annotations(request: WSGIRequest):
    """Saves the annotation state of provided elements and triggers download if it is a web image that is not
    existent in the database.

    The post data must contain the parameter "elements" and "class_id" which need to be specified in the following way:

    | elements: [
          {
              id: 1,
              url: "http://example.com/test.jpg",
              annotation: {
                  difficult: 0,
                  groundtruth: 1
              }
          },
          ...
       ]
    | class_id: 1


    The following table lists the derived action from annotation values:

    =========  ===========  ======================
    difficult  groundtruth  action
    =========  ===========  ======================
    false      false        annotation 'negative'
    false      true         annotation 'positive'
    true       false        annotation 'difficult'
    true       true         delete annotation
    =========  ===========  ======================

    :param request: the request
    :return: 200 if ok otherwise a bad request
    """
    if request.is_ajax() and request.method == "POST" and request.content_type == "application/json":
        post_json = json.loads(request.body)
        if "class_id" not in post_json or "elements" not in post_json:
            return HttpResponseBadRequest("Invalid request")
        class_id = post_json['class_id']
        for image in post_json['elements']:
            if "id" in image:
                image_obj = Image.objects.get(id=image['id'])
                try:
                    if image_obj.imageurl.error:
                        add_image_to_download_queue(image_obj.imageurl, request)
                except ObjectDoesNotExist:
                    pass
            elif "url" in image:
                image_url_obj = create_new_web_image(image['url'])
                add_image_to_download_queue(image_url_obj, request)
                image_obj = image_url_obj.imageid
            else:
                return HttpResponseBadRequest("Wrong element structure!")
            if image['annotation']['difficult'] and image['annotation']['groundtruth']:
                delete_image_annotation(image_obj, class_id)
            else:
                set_image_annotation(image_obj, class_id, image['annotation']['difficult'],
                                     image['annotation']['groundtruth'], request)
        return HttpResponse("OK")
    return HttpResponseBadRequest("Invalid request")


def data_import_query(class_type_id: int) -> Callable[[WSGIRequest], HttpResponse]:
    def import_query_data(request: WSGIRequest) -> HttpResponse:
        grid_elements = []
        file = ''
        try:
            file = request.FILES["upload"]
        except MultiValueDictKeyError:
            pass

        if file and allowed_file(file.name):
            data, allowed_columns = read_csv(file)
            if allowed_columns:
                for el in data:
                    video_name, frame_start, frame_end = el
                    try:
                        video = Video.objects.get(path=video_name)
                        frame_set = Videoframe.objects.filter(videoid=video.id).filter(
                            number__range=[frame_start, frame_end]).order_by('number')

                    except ObjectDoesNotExist:
                        continue
                    for frame in frame_set:
                        try:
                            img = Image.objects.get(id=frame.imageid.id)
                            grid_elements.append(img)
                        except ObjectDoesNotExist:
                            pass

        serialized_images_dict = serialize_images(grid_elements, request, return_dict=True,
                                                  additional_value_function=add_absolute_image_path)

        if class_type_id == FaceRecognitionConfig.class_type_id:
            serialized_images_dict['elements'] = update_face_list(serialized_images_dict['elements'])
            serialized_images_dict = update_groundtruth_annotation(
                serialized_images_dict,
                request.session[SessionConfig.SELECTED_PERSON_SESSION_KEY],
                mode="bbox")

        return HttpResponse(json.dumps(serialized_images_dict))

    return import_query_data


def model_evaluation(class_type_id: int) -> Callable[[WSGIRequest], HttpResponse]:
    """Get the average precisions per class from database for the given classtype and show them in a chart
    :param class_type_id the class type id of the current app
    :return: the rendered template for a model evaluation
    """

    def model_evaluation_data(request: WSGIRequest) -> HttpResponse:
        def sort_model_evaluations(first_model, second_model):
            """Get the average precisions per concept from database and show them in a chart
            :param first_model: the model determining the order of classes
            :param second_model: the model to be compared to first_model
            :return (sorted_apcs, compared_apcs): the APs for each model sorted by the values in sorted_apcs
            """
            sorted_classes, compared_apcs = [], []
            sorted_apcs = list(ordered_query.filter(modelid=first_model.id))
            # force evaluation to get all objects at once
            compared_classes = dict(ordered_query.filter(modelid=second_model.id))
            for new_cls, prec in sorted_apcs:
                sorted_classes.append(new_cls)
                apc = compared_classes.get(new_cls)
                compared_apcs.append((new_cls, 0 if apc is None else apc))
            for comp_cls in compared_classes:
                if comp_cls not in sorted_classes:
                    sorted_apcs.append((comp_cls, 0))
                    compared_apcs.append((comp_cls, compared_classes.get(comp_cls)))
            return sorted_apcs, compared_apcs

        old_apcs, new_apcs = [], []
        sort_mode = "old_aps"
        ordered_query = Evaluation.objects.order_by('-precision').values_list('classid__name', 'precision')
        models = Model.objects.filter(evaluation__classid__classtypeid=class_type_id)
        n_models = models.distinct('id').count()
        if n_models == 1:
            model = models.latest('date')
            sort_mode = request.COOKIES.get("eval_sort_mode", "old_aps")
            if sort_mode == 'alphabetically':
                old_apcs = ordered_query.filter(modelid=model.id).order_by('classid__name').distinct('classid__name')
            else:
                old_apcs = ordered_query.filter(modelid=model.id)
                sort_mode = 'old_aps'
        elif n_models > 1:
            new_model = models.latest('date')
            old_model = models.exclude(id=new_model.id).latest('date')
            sort_mode = request.COOKIES.get("eval_sort_mode", "new_aps")
            if sort_mode == 'new_aps':
                new_apcs, old_apcs = sort_model_evaluations(new_model, old_model)
            elif sort_mode == 'old_aps':
                old_apcs, new_apcs = sort_model_evaluations(old_model, new_model)
            elif sort_mode == 'alphabetically':
                joined_classes = Evaluation.objects.filter(modelid__in=(old_model.id, new_model.id)) \
                    .order_by('classid__name').distinct('classid__name').values_list('classid__name', 'classid__id')
                old_evaluations = dict(
                    Evaluation.objects.filter(modelid=old_model.id).values_list('classid', 'precision'))
                new_evaluations = dict(
                    Evaluation.objects.filter(modelid=new_model.id).values_list('classid', 'precision'))
                for cls_name, cls_id in joined_classes:
                    old_apc, new_apc = old_evaluations.get(cls_id), new_evaluations.get(cls_id)
                    old_apcs.append((cls_name, 0 if old_apc is None else round(old_apc, 3)))
                    new_apcs.append((cls_name, 0 if new_apc is None else round(new_apc, 3)))
        new_overall_ap = 0 if len(new_apcs) == 0 else round(mean(apc[1] for apc in new_apcs), 3)
        overall_ap = 0 if len(old_apcs) == 0 else round(mean(apc[1] for apc in old_apcs), 3)

        return render(request, "page/model-evaluation.html",
                      {'old_precisions_per_class': old_apcs, 'new_precisions_per_class': new_apcs,
                       'old_overall_ap': overall_ap, 'new_overall_ap': new_overall_ap, 'eval_sort_mode': sort_mode})

    return model_evaluation_data


def add_prediction_score(image_dict: dict, image: Image, model_id: int, class_id: int) -> None:
    """Add the prediction score for a given image, model and class to the serialized dictionary

    :param image_dict: the serialized dictionary entry
    :param image: the image database object
    :param model_id: the id of the model
    :param class_id: the id of the class
    """
    image_dict.update({
        GridConfig.ELEMENT_ADDITIONAL_VALUE_SCORE:
            image.imageprediction_set.filter(modelid=model_id, classid=class_id).first().score
    })


def retrieval_query(class_type_id: int) -> Callable[[WSGIRequest], HttpResponse]:
    def retrieval_query_data(request: WSGIRequest) -> HttpResponse:
        class_type_name = Classtype.objects.get(id=class_type_id).name.lower()
        if not request.is_ajax() or request.method != "POST" or \
                not all(x in request.POST for x in [class_type_name, 'asc', 'annotations']):
            return HttpResponseBadRequest("Wrong request method or missing parameter!")
        try:
            class_id = int(request.POST[class_type_name])
        except ValueError:
            return HttpResponseBadRequest("Class ID needs to be an integer!")
        s_class = Class.objects.get(id=class_id)
        s_ascending = request.POST['asc'] == "1"
        s_annotations = request.POST['annotations'] == "1"
        evaluation_classtypeid = Evaluation.objects.filter(classid__classtypeid_id=class_type_id).values_list('id',
                                                                                                              flat=True)
        latest_model = Model.objects.filter(evaluation__in=evaluation_classtypeid, inference_stored=True).latest('date')
        predictions = Imageprediction.objects \
            .filter(classid=s_class, modelid=latest_model.id) \
            .order_by('score' if s_ascending else '-score')
        if not s_annotations:
            # the image can be annotated for another class - so there might exist an image annotation but without a
            # matching class id
            predictions = predictions.filter(~Q(imageid__imageannotation__classid=s_class) |
                                             Q(imageid__imageannotation__isnull=True))
        return HttpResponse(serialize_images(
            predictions, request, lambda x: x.imageid,
            lambda image_dict, image: add_prediction_score(image_dict, image, latest_model.id, s_class.id)
        ))

    return retrieval_query_data


def export_file(request: WSGIRequest) -> HttpResponseBase:
    """Deliver the export zip file for a given app and threshold - results in 404 if file is not existent

    :param request: the WSGIRequest
    :return: the file response
    """
    if request.method != "GET" or any([x not in request.GET for x in ['app', 'threshold']]):
        return HttpResponseBadRequest("Wrong request method or missing parameter!")
    if request.GET['app'] not in [ConceptClassificationConfig.name, FaceRecognitionConfig.name]:
        return HttpResponseBadRequest("Wrong parameter value!")
    try:
        threshold = int(request.GET['threshold'])
    except ValueError:
        return HttpResponseBadRequest("Wrong parameter value!")
    app_context = request.GET['app']
    if app_context == ConceptClassificationConfig.name:
        class_type_name = os.environ['EXPORT_FILE_PREFIX_CC']
    else:
        class_type_name = os.environ['EXPORT_FILE_PREFIX_FR']
    redis_con = redis.Redis(connection_pool=KerasFlaskConfig.redis_connection_pool)
    model_ident = redis_con.get(os.environ['REDIS_KEY_EXPORT_MODEL_IDENT'].format(app_context))
    file_ident = "{:s}_{:s}".format(class_type_name, model_ident or "")
    redis_con.close()
    if not model_ident:
        raise Http404
    file_name = "{:s}_{:d}.zip".format(file_ident, threshold)
    file_path = os.path.join(os.environ['EXPORT_MOUNT_PATH'], file_name)
    if not os.path.isfile(file_path):
        raise Http404
    return FileResponse(open(file_path, "rb"), as_attachment=True, filename=file_name)
