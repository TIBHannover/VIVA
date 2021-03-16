import json
import os

import redis
import requests
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.handlers.wsgi import WSGIRequest
from django.db import IntegrityError
from django.db.models import Count
from django.forms import ModelForm
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import render
from django.urls import reverse_lazy
from django_jinja.views.generic import ListView, CreateView, UpdateView
from typing import Callable

from base.models import Class, Classtype, Image, Videoframe, Video, serialize_images, Imageurl, Model, \
    Imageprediction, Collection, Bboxannotation, Evaluation
from base.tools import webimagecrawler
from base.tools.imageannotation import create_new_web_image
from base.tools.webimagedownloader import add_image_to_download_queue
from face_recognition.apps import FaceRecognitionConfig
from face_recognition.classifier.classifier import train_classifier, classify
from face_recognition.face_detection.bboxannotation import set_image_bbox, delete_image_bbox
from face_recognition.face_detection.face_detection import update_face_list, create_image_encodings, \
    reset_counters, update_face_list_from_db, update_groundtruth_annotation
from face_recognition.similarity_search.similarity_search_faiss import similarity_search_handle_request
from viva.settings import DEBUG, SessionConfig, DB_CRAWLER_COLLECTION_ID, MEDIA_ROOT, \
    PersonTrainInferConfig, KerasFlaskConfig


def add_absolute_image_path(image_dict: dict, image: Image) -> None:
    """Adds the absolute path of the serialized images to the dictionary
    :param image_dict: the dictionary of the current image
    :param image: the current image object
    """
    image_dict.update({
        "path": image.path.path.strip("/")
    })


class PersonForm(ModelForm):
    class Meta:
        model = Class
        fields = ['name', 'description']


class PersonListView(ListView):
    model = Class
    template_name = "face_recognition/person-selection.html"
    context_object_name = "collection_persons"

    def get_queryset(self):
        return Class.objects.filter(classtypeid=FaceRecognitionConfig.class_type_id).order_by('name')


class PersonCreateView(CreateView):
    model = Class
    template_name = "face_recognition/add-person.html"
    fields = ['name', 'description', 'classtypeid']
    success_url = reverse_lazy("face_recognition:add_person")

    def get_context_data(self, **kwargs):
        kwargs['object_list'] = Classtype.objects.order_by('name')
        return super(PersonCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        form.instance.classtypeid = Classtype.objects.get(id=FaceRecognitionConfig.class_type_id)
        try:
            return super(PersonCreateView, self).form_valid(form)
        except IntegrityError:
            return HttpResponseServerError("Person name already exists!")


class PersonEditView(SuccessMessageMixin, UpdateView):
    form_class = PersonForm
    model = Class
    template_name = "page_elements/edit-class.html"
    context_object_name = "collection_persons"
    success_url = reverse_lazy('face_recognition:data_person_selection')

    def form_valid(self, form):
        form.instance.description = None if form.instance.description == "" else form.instance.description
        return super().form_valid(form)


class RetrievalView(PersonListView):
    template_name = "face_recognition/retrieval.html"

    def get_context_data(self, **kwargs):
        context = super(RetrievalView, self).get_context_data(**kwargs)
        context.update({'retrieval_exists': Model.objects.filter(
            inference_stored=True,
            evaluation__classid__classtypeid=FaceRecognitionConfig.class_type_id).exists()})
        return context


def select_person(request):
    """This method writes the posted selected person into the session.
    :parameter request: the request
    """
    if request.method == 'POST' and request.is_ajax():
        request.session[SessionConfig.SELECTED_PERSON_SESSION_KEY] = Class.objects.get(
            name=request.POST.get('person')).id
        return HttpResponse()
    return HttpResponseBadRequest()


def export(request):
    """Export image predictions of last person model to csv file.
    :parameter request: the request
    """
    return render(request, 'face_recognition/export.html',
                  {'retrieval_exists': Model.objects.filter(
                      inference_stored=True,
                      evaluation__classid__classtypeid=FaceRecognitionConfig.class_type_id).exists(),
                   "default_threshold": 0.8})


def export_query(request):
    def prepare_export_data(prediction_list):

        def covert_frame2tc(frame):
            fpms = 25 / 1000
            tc = int(frame / fpms)
            return tc

        result_lst = [["personname", "videopath", "start(ms)", "duration(ms)", "score"]]
        for prediction in prediction_list:
            person_name, videoid, framenumber, score = prediction[:]
            videopath = Video.objects.get(id=videoid).path
            result_lst.append(['\"' + person_name + '\"', videopath, covert_frame2tc(framenumber), 40, score])
        return result_lst

    if request.is_ajax() and request.method == 'POST' and \
            all(x in request.POST for x in ["export_threshold"]):

        evaluation_person = Evaluation.objects.filter(
            classid__classtypeid_id=FaceRecognitionConfig.class_type_id).values_list('id', flat=True)
        if evaluation_person.exists():
            try:
                latest_model = Model.objects.filter(evaluation__in=evaluation_person, inference_stored=True).latest(
                    'date')
                predictions = list(
                    Imageprediction.objects.filter(modelid=latest_model.id, score__gte=request.POST["export_threshold"]) \
                        .values_list('classid__name', 'imageid__videoframe__videoid_id',
                                     'imageid__videoframe__number', 'score').order_by('imageid__path',
                                                                                      'score'))
                predictions = prepare_export_data(predictions)
            except ObjectDoesNotExist:
                pass

        return HttpResponse(json.dumps(predictions))
    return HttpResponseBadRequest()


# TODO: call this method when inference state changes (in face recognition app)
def export_client_update() -> None:
    """Send an internal request that will send a server side event to clients to update the export page of the
    face recognition app
    """
    requests.post(KerasFlaskConfig.Flask.URL_INTERNAL + KerasFlaskConfig.Flask.Export.URL_UPDATE + "?app="
                  + FaceRecognitionConfig.name)


# TODO?: On inference page check if an export is currently running
def export_running() -> bool:
    """Returns whether the export for the face recognition app is currently running or not
    """
    redis_con = redis.Redis(connection_pool=KerasFlaskConfig.redis_connection_pool)
    exp_run = redis_con.get(
        int(redis_con.get(os.environ['REDIS_KEY_EXPORT_RUN'].format(FaceRecognitionConfig.name)) or 0) == 1)
    redis_con.close()
    return exp_run


def data_import(request):
    """Import keyframes from from csv/excel and display them in grid.
    :parameter request: the request
    """
    return render(request, 'face_recognition/data-import.html',
                  {'class_id': request.session[SessionConfig.SELECTED_PERSON_SESSION_KEY]})


def similarity_search(request):
    """Perform similarity search and annotate the results."""
    return render(request, 'face_recognition/data-similarity-search.html',
                  {'class_id': request.session[SessionConfig.SELECTED_PERSON_SESSION_KEY]})


def similarity_search_query(request):
    simsearch_dict = similarity_search_handle_request(request)
    serialized_images_dict = serialize_images(simsearch_dict['images'], request, return_dict=True,
                                              additional_value_function=add_absolute_image_path)

    serialized_images_dict = update_groundtruth_annotation(serialized_images_dict, request.session[
        SessionConfig.SELECTED_PERSON_SESSION_KEY], mode="bbox", bbox_lst=simsearch_dict["bbox_check_list"])
    serialized_images_dict['time'] = simsearch_dict['time']

    return HttpResponse(json.dumps(serialized_images_dict))


def review(groundtruth: bool) -> Callable[[WSGIRequest], HttpResponse]:
    """Returns a function that renders the review template for a request where the reviewed annotations have to match
    the given conditions (groundtruth).
    :param groundtruth: which groundtruth label should the annotations match
    :return:
    """

    def review_data(request: WSGIRequest) -> HttpResponse:
        return render(request, 'face_recognition/data-review.html',
                      {'grundtruth': groundtruth,
                       'class_id': request.session[SessionConfig.SELECTED_PERSON_SESSION_KEY]})

    return review_data


def review_query(request: WSGIRequest):
    """Delivers a HTTP response that contains only images wherefore it exists a specified annotation
    (groundtruth) for the current selected class (stored in session). Conditions were specified by
    HTTP Post method parameters.

    :param request: the request
    :return: serialized images (JSON) that match the conditions
    """
    if request.is_ajax() and request.method == "POST" and all(x in request.POST for x in ['groundtruth']):

        bbox_objects = Bboxannotation.objects.filter(classid_id=request.session[
            SessionConfig.SELECTED_PERSON_SESSION_KEY]).order_by('-imageid')
        serialized_images_dict = serialize_images(bbox_objects, request, lambda x: x.imageid, return_dict=True,
                                                  additional_value_function=add_absolute_image_path)

        serialized_images_dict = update_groundtruth_annotation(serialized_images_dict, request.session[
            SessionConfig.SELECTED_PERSON_SESSION_KEY], mode="image")

        if 'face' in request.COOKIES.keys():
            if request.COOKIES['face'] != 'photo':
                serialized_images_dict['elements'] = update_face_list_from_db(serialized_images_dict['elements'],
                                                                              bbox_objects)

        return HttpResponse(json.dumps(serialized_images_dict))
    return HttpResponseBadRequest()


def train_server_template(template, request):
    res = render(request, template, {'FACE_SERVICE_URL': PersonTrainInferConfig.URL, 'DJANGO_DEBUG': DEBUG})
    return res


def start_training(request):
    if request.method == 'POST':
        reset_counters()
        images = []
        class_lst = []
        bbox_lst = []

        all_classes = Class.objects.filter(classtypeid=FaceRecognitionConfig.class_type_id)
        for class_object in all_classes:
            bbox_annotations = Bboxannotation.objects.filter(classid=class_object)
            if PersonTrainInferConfig.MIN_ANNOTATIONS <= len(bbox_annotations):
                for bbox_anno in bbox_annotations:
                    bbox_lst.append(bbox_anno)
                    class_lst.append(class_object.id)
                    images.append(Image.objects.get(id=bbox_anno.imageid.id))

        images_dict = serialize_images(images, request, return_dict=True,
                                       additional_value_function=add_absolute_image_path)

        for idx, element in enumerate(images_dict['elements']):
            element.update({
                'classid': class_lst[idx],
                'bbox': {"x": bbox_lst[idx].x, "y": bbox_lst[idx].y, "w": bbox_lst[idx].w, "h": bbox_lst[idx].h}
            })
        images_dict['count'] = len(images_dict['elements'])

        create_image_encodings(images_dict['elements'], training=True)

        train_classifier()

        return HttpResponse()
    return HttpResponseBadRequest()


def start_inference(request):
    """
    Starts the face processing for all available videoframes in the database
    :param request: the request
    :return:
    """
    if request.method == 'POST':
        reset_counters()
        # Inference is conducted on video keyframes only, excluding web or other kind of images
        videoframes = Videoframe.objects.all().values_list("id", flat=True)
        all_images = list(Image.objects.filter(videoframe__in=videoframes))

        all_images_dict = serialize_images(all_images, request, return_dict=True,
                                           additional_value_function=add_absolute_image_path)

        all_images_dict['elements'] = update_face_list(all_images_dict['elements'],
                                                       is_inference=True,
                                                       user=request.user)

        all_images_dict['count'] = len(all_images_dict['elements'])

        create_image_encodings(all_images_dict['elements'], training=False)
        return HttpResponse()
    return HttpResponseBadRequest()


def classify_persons(request):
    """
    Writes the classifications as image_predictions into the database
    :param request:
    :return:
    """
    if request.method == 'POST':
        return classify(request)
    return HttpResponseBadRequest()


def web_search_query(request):
    if request.is_ajax() and request.method == 'POST' and \
            all(x in request.POST for x in ["text", "max", "license"]) and request.POST['license'] in [
            "default", "noncommercial"]:
        try:
            max_value = int(request.POST['max'])
        except ValueError:
            return HttpResponseBadRequest()
        links, search_engine = webimagecrawler.crawl(request.META['HTTP_USER_AGENT'], request.POST['text'],
                                                     max_value, 'face',
                                                     request.POST['license'])
        images = {'elements': [], 'count': len(links), 'engine': search_engine}
        for link in links:
            image = {
                'media_type': 'image',
                'download_url': link
            }
            try:
                db_image = Imageurl.objects.get(url=link)
                if not db_image.error:
                    image.update({
                        'id': db_image.imageid.id,
                        'url': db_image.imageid.path.url,
                        'downloaded': db_image.downloaded,
                        'download_error': db_image.error
                    })
                else:
                    image.update({
                        'downloaded': False
                    })
            except ObjectDoesNotExist:
                image.update({
                    'downloaded': False
                })
                pass
            except MultipleObjectsReturned:
                pass
            images['elements'].append(image)

        images['elements'] = update_face_list(images['elements'], is_web=True)
        images = update_groundtruth_annotation(images, request.session[
            SessionConfig.SELECTED_PERSON_SESSION_KEY], mode="bbox")
        images['count'] = len(images['elements'])

        return HttpResponse(json.dumps(images))
    return HttpResponseBadRequest()


def model_dataset_overview(request):
    """Provide a dataset overview by listing positive and negative annotations per concept
    :param request: the request
    :return: the rendered template for a dataset overview
    """
    dataset_distribution = Bboxannotation.objects.exclude(classid__isnull=True).values('classid__name').annotate(
        positives=Count('classid__name')).order_by('-positives')

    cutoff_idx = -1
    for idx, entry in enumerate(dataset_distribution):
        entry['negatives'] = 0
        if entry['positives'] < PersonTrainInferConfig.MIN_ANNOTATIONS and cutoff_idx == -1:
            cutoff_idx = idx

    return render(request, "page/model-dataset.html",
                  {"dataset_distribution": dataset_distribution, "cutoff_samples_idx": cutoff_idx,
                   "min_class_samples": PersonTrainInferConfig.MIN_ANNOTATIONS})


def save_grid_annotation_bbox(request: WSGIRequest):
    """Saves the annotation state and the bounding boxes of provided elements and triggers download if it is a web image
    that is not existent in the database.

    The post data must contain the parameter "elements" and "class_id" which need to be specified in the following way:

    | elements: [
          {
              id: 1,
              url: "http://example.com/test.jpg",
              annotation: {
                  groundtruth: 1
              }
              bbox: {
                x: 10,
                y: 10,
                w: 100,
                h: 100
              }
          },
          ...
       ]
    | class_id: 1

    :param request: the request
    :return: 200 if ok otherwise a bad request
    """
    if request.is_ajax() and request.method == "POST" and request.content_type == "application/json":
        post_json = json.loads(request.body)
        if "class_id" not in post_json or "elements" not in post_json:
            return HttpResponseBadRequest("Invalid request")
        class_id = post_json['class_id']
        for image in post_json['elements']:
            if "bbox" not in image:
                return HttpResponseBadRequest("Wrong element structure!")
            # case that web image already exists in db
            if "id" in image:
                image_obj = Image.objects.get(id=image['id'])
                try:
                    if image_obj.imageurl.error:
                        add_image_to_download_queue(image_obj.imageurl, request)
                except ObjectDoesNotExist:
                    pass
            elif "url" in image:
                os.makedirs(os.path.join(MEDIA_ROOT, Collection.objects.get(id=DB_CRAWLER_COLLECTION_ID).basepath),
                            exist_ok=True)
                image_url_obj = create_new_web_image(image['url'])
                add_image_to_download_queue(image_url_obj, request)
                image_obj = image_url_obj.imageid
            else:
                return HttpResponseBadRequest("Wrong element structure!")

            if not image['annotation']['groundtruth']:
                delete_image_bbox(image_obj, class_id, image['bbox'])
            else:
                set_image_bbox(image_obj, class_id, image['bbox'], request)
        return HttpResponse("OK")
    return HttpResponseBadRequest("Invalid request")
