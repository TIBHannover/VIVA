"""face_recognition URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, reverse_lazy
from django.views.generic import TemplateView, RedirectView

import base.views
from base.decorators import person_selected
from base.tools.checks import group_required, is_user_authenticated
from face_recognition.apps import FaceRecognitionConfig
from . import views

app_name = FaceRecognitionConfig.name

urlpatterns = [
    # TODO: This is not a solution if an user is not in "Annotator" group!
    path("", RedirectView.as_view(url=reverse_lazy("face_recognition:data_person_selection")), name="start"),
    path("data/selection", views.PersonListView.as_view(), name="data_person_selection",
         kwargs={"check": group_required("Annotator")}),
    path("data/selection/save", views.select_person, name="select_person",
         kwargs={"check": group_required("Annotator")}),
    path("data/selection/add_person", views.PersonCreateView.as_view(), name="add_person",
         kwargs={"check": group_required("Annotator")}),
    path('data/selection/edit_person/<int:pk>', views.PersonEditView.as_view(), name="edit_person",
         kwargs={"check": group_required("Annotator")}),
    path('data/selection/delete_person/<int:pk>', views.PersonListView.as_view(), name="delete_person",
         kwargs={"check": group_required("Annotator")}),

    path("data/sequence_annotation", person_selected(views.data_import, "face_recognition:data_person_selection"),
         name="data_sequence_annotation"),
    path("data/sequence_annotation/query",
         person_selected(base.views.data_import_query(class_type_id=FaceRecognitionConfig.class_type_id),
                         "face_recognition:data_person_selection"),
         name="data_sequence_annotation_query", kwargs={"check": group_required("Annotator")}),

    path("data/webcrawler",
         person_selected(TemplateView.as_view(template_name='face_recognition/data-web-image-acquisition.html'),
                         "face_recognition:data_person_selection"), name="data_webcrawler"),
    path("data/webcrawler/query", views.web_search_query, name="data_web_crawler_query",
         kwargs={"check": group_required("Annotator")}),

    path("data/similarity_search",
         person_selected(views.similarity_search, f"{app_name}:data_person_selection"),
         name="data_similarity_search"),
    path("data/similarity_search/query", views.similarity_search_query, name="data_similarity_search_query",
         kwargs={"check": group_required("Annotator")}),

    path("data/review_positive",
         person_selected(views.review(True), "face_recognition:data_person_selection"),
         name="data_review", kwargs={"check": group_required("Annotator")}),
    path("data/review/query",
         person_selected(views.review_query, "face_recognition:data_person_selection"),
         name="data_review_query", kwargs={"check": group_required("Annotator")}),
    path("model/dataset_overview", views.model_dataset_overview,
         name="model_dataset_overview", kwargs={"check": group_required("Trainer")}),
    path("model/training",
         lambda req: views.train_server_template("face_recognition/model-training.html", req),
         name="model_training", kwargs={"check": group_required("Trainer")}),
    path("model/training/start", views.start_training,
         name="model_training_start",
         kwargs={"check": group_required("Trainer")}),
    path("model/evaluation", base.views.model_evaluation(class_type_id=FaceRecognitionConfig.class_type_id),
         name="model_evaluation", kwargs={"check": group_required("Trainer")}),
    path("model/inference",
         lambda req: views.train_server_template("face_recognition/model-inference.html", req),
         name="model_inference"),
    path("model/inference/start", views.start_inference,
         name="model_inference_start",
         kwargs={"check": group_required("Trainer")}),
    path("model/inference/classify_persons", views.classify,
         name="model_classify_persons",
         kwargs={"check": group_required("Trainer")}),

    path("retrieval", views.RetrievalView.as_view(), name="retrieval"),
    path("retrieval/query", base.views.retrieval_query(class_type_id=FaceRecognitionConfig.class_type_id),
         name="retrieval_query",
         kwargs={"check": group_required("Annotator")}),

    path("export", TemplateView.as_view(template_name="page/export.html"), name="export"),

    path('api/save_grid_annotation_bbox', views.save_grid_annotation_bbox,
         name='save-grid-annotation-bbox', kwargs={"check": is_user_authenticated()})
]
