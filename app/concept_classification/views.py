import json
from typing import Callable

from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.handlers.wsgi import WSGIRequest
from django.db import IntegrityError
from django.db.models import Case, Count, When
from django.forms import ModelForm
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import render
from django.urls import reverse_lazy
from django_jinja.views.generic import CreateView, ListView, UpdateView

from base.models import Class, Classtype, Imageannotation, Imageurl, Model, serialize_images
from base.tools import webimagecrawler
from concept_classification.apps import ConceptClassificationConfig
from concept_classification.similarity_search.search import SearchMode, search
from viva.settings import SessionConfig, KerasFlaskConfig


class ConceptForm(ModelForm):
    class Meta:
        model = Class
        fields = ['name', 'description']


class ConceptListView(ListView):
    model = Class
    template_name = "concept_classification/concept-selection.html"
    context_object_name = "collection_concepts"

    def get_queryset(self):
        return Class.objects.filter(classtypeid=ConceptClassificationConfig.class_type_id).order_by('name')


class ConceptCreateView(CreateView):
    model = Class
    template_name = "concept_classification/add-concept.html"
    fields = ['name', 'description', 'classtypeid']
    success_url = reverse_lazy("concept_classification:add_concept")

    def get_context_data(self, **kwargs):
        kwargs['object_list'] = Classtype.objects.order_by('name')
        return super(ConceptCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        form.instance.classtypeid = Classtype.objects.get(id=ConceptClassificationConfig.class_type_id)
        try:
            return super(ConceptCreateView, self).form_valid(form)
        except IntegrityError:
            return HttpResponseServerError("Concept name already exists!")


class ConceptEditView(SuccessMessageMixin, UpdateView):
    form_class = ConceptForm
    model = Class
    template_name = "page_elements/edit-class.html"
    context_object_name = "collection_concepts"
    success_url = reverse_lazy('concept_classification:data_concept_selection')

    def form_valid(self, form):
        form.instance.description = None if form.instance.description == "" else form.instance.description
        return super().form_valid(form)


class RetrievalView(ConceptListView):
    template_name = "concept_classification/retrieval.html"

    def get_context_data(self, **kwargs):
        context = super(RetrievalView, self).get_context_data(**kwargs)
        context.update({'retrieval_exists': Model.objects.filter(
            inference_stored=True,
            evaluation__classid__classtypeid=ConceptClassificationConfig.class_type_id).exists()})
        return context


def select_concept(request):
    """This method writes the posted selected concept into the session.
    :parameter request: the request
    """
    if request.method == 'POST' and request.is_ajax():
        try:
            request.session[SessionConfig.SELECTED_CONCEPT_SESSION_KEY] = Class.objects.get(
                name=request.POST.get('concept'), classtypeid=ConceptClassificationConfig.class_type_id).id
        except ObjectDoesNotExist:
            return HttpResponse(status=422)
        return HttpResponse()
    return HttpResponseBadRequest()


def data_import(request):
    """Import keyframes from from csv/excel and display them in grid.
    :parameter request: the request
    """
    return render(request, 'concept_classification/data-import.html',
                  {'class_id': request.session[SessionConfig.SELECTED_CONCEPT_SESSION_KEY]})


def similarity_search(request):
    """Perform similarity search and annotate the results."""
    return render(request, 'concept_classification/data-similarity-search.html',
                  {'class_id': request.session[SessionConfig.SELECTED_CONCEPT_SESSION_KEY]})


def similarity_search_query(request):
    if request.is_ajax() and request.method == "POST" and \
            all(x in request.POST for x in ['mode', 'url', 'select', 'max']):
        try:
            max_results = int(request.POST['max'])
        except ValueError:
            return HttpResponseBadRequest()
        mode = request.POST['mode']
        if mode == "upload":
            if "file" not in request.FILES:
                return HttpResponseBadRequest("No file specified")
            similarity_search_result = search(SearchMode.UPLOAD, request.FILES['file'], max_results)
        elif mode == "url":
            similarity_search_result = search(SearchMode.URL, request.POST['url'], max_results)
        elif mode == "select":
            similarity_search_result = search(SearchMode.DB_IMAGE, request.POST['select'], max_results)
        else:
            return HttpResponseBadRequest()
        if similarity_search_result['error']:
            return HttpResponseBadRequest(similarity_search_result['error'])
        serialized_images = serialize_images(similarity_search_result['images'], request, return_dict=True)
        serialized_images['time'] = similarity_search_result['time']
        return HttpResponse(json.dumps(serialized_images))
    return HttpResponseBadRequest()


def review(difficult: bool, groundtruth: bool) -> Callable[[WSGIRequest], HttpResponse]:
    """Returns a function that renders the review template for a request where the reviewed annotations have to match
    the given conditions (difficult, groundtruth).

    :param difficult: whether an annotation needs to be difficult or not
    :param groundtruth: which label should be matched by the annotations (only relevant if difficult = false)
    :return:
    """

    def review_data(request: WSGIRequest) -> HttpResponse:
        return render(request, 'concept_classification/data-review.html',
                      {'difficult': difficult, 'groundtruth': groundtruth, 'review': True,
                       'class_id': request.session[SessionConfig.SELECTED_CONCEPT_SESSION_KEY]})

    return review_data


def review_query(request: WSGIRequest):
    """Delivers a HTTP response that contains only images wherefore it exists a specified annotation
    (difficult, groundtruth) for the current selected class (stored in session). Conditions were specified by
    HTTP Post method parameters.

    :param request: the request
    :return: serialized images (JSON) that match the conditions
    """
    if request.is_ajax() and request.method == "POST" and all(x in request.POST for x in ['difficult', 'groundtruth']):
        return HttpResponse(
            serialize_images(
                Imageannotation.objects.filter(
                    groundtruth=request.POST['groundtruth'] == "1",
                    difficult=request.POST['difficult'] == "1",
                    classid_id=request.session[SessionConfig.SELECTED_CONCEPT_SESSION_KEY]
                ).order_by('-imageid'),
                request,
                image_extractor=lambda x: x.imageid
            )
        )
    return HttpResponseBadRequest()


def web_search_query(request):
    if request.is_ajax() and request.method == 'POST' and \
            all(x in request.POST for x in ["text", "type", "max", "license"]) and \
            request.POST['type'] in ["default", "face", "photo"] and \
            request.POST['license'] in ["default", "noncommercial"]:
        try:
            max_value = int(request.POST['max'])
        except ValueError:
            return HttpResponseBadRequest()
        links, search_engine = webimagecrawler.crawl(request.META['HTTP_USER_AGENT'], request.POST['text'], max_value,
                                                     request.POST['type'], request.POST['license'])
        images = {'elements': [], 'count': len(links), 'engine': search_engine}
        for link in links:
            image = {
                'media_type': 'image',
                'download_url': link
            }
            try:
                db_image = Imageurl.objects.get(url=link)
                image.update({
                    'id': db_image.imageid.id,
                    'url': db_image.imageid.path.url,
                    'downloaded': db_image.downloaded,
                    'download_error': db_image.error
                })
                cls_id = request.session[SessionConfig.SELECTED_CONCEPT_SESSION_KEY]
                image_annotation_set = db_image.imageid.imageannotation_set.filter(classid_id=cls_id)
                if image_annotation_set.exists():
                    image.update({
                        'annotation': {
                            'difficult': image_annotation_set.first().difficult,
                            'groundtruth': image_annotation_set.first().groundtruth
                        }
                    })
            except ObjectDoesNotExist:
                image.update({
                    'downloaded': False
                })
                pass
            images['elements'].append(image)
        return HttpResponse(json.dumps(images))
    return HttpResponseBadRequest()


def model_dataset_overview(request):
    """Provide a dataset overview by listing positive and negative annotations per concept

    :param request: the request
    :return: the rendered template for a dataset overview
    """
    dataset_distribution = Imageannotation.objects.filter(
        difficult=False,
        classid__classtypeid=ConceptClassificationConfig.class_type_id) \
        .values('classid__name') \
        .annotate(positives=Count(Case(When(groundtruth=True, then=1))),
                  negatives=Count(Case(When(groundtruth=False, then=1)))) \
        .order_by('-positives', '-negatives')
    cutoff_idx = -1
    for idx, entry in enumerate(dataset_distribution):
        if entry['positives'] < KerasFlaskConfig.Training.MIN_ANNOTATIONS:
            cutoff_idx = idx
            break
    return render(request, "page/model-dataset.html",
                  {"dataset_distribution": dataset_distribution, "cutoff_samples_idx": cutoff_idx,
                   "min_class_samples": KerasFlaskConfig.Training.MIN_ANNOTATIONS})
