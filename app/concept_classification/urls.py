"""concept_classification URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path("", views.home, name="home")
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path("", Home.as_view(), name="home")
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path("blog/", include("blog.urls"))
"""
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView, TemplateView

import base.views
from base.decorators import concept_selected
from base.tools.checks import group_required
from concept_classification.apps import ConceptClassificationConfig
from . import views

app_name = ConceptClassificationConfig.name

urlpatterns = [
    # TODO: This is not a solution if an user is not in "Annotator" group!
    path("", RedirectView.as_view(url=reverse_lazy(f"{app_name}:data_concept_selection")), name="start"),
    path("data/selection", views.ConceptListView.as_view(), name="data_concept_selection",
         kwargs={"check": group_required("Annotator")}),
    path("data/selection/save", views.select_concept, name="select_concept",
         kwargs={"check": group_required("Annotator")}),
    path("data/selection/add_concept", views.ConceptCreateView.as_view(), name="add_concept",
         kwargs={"check": group_required("Annotator")}),
    path('data/selection/edit_concept/<int:pk>', views.ConceptEditView.as_view(), name="edit_concept",
         kwargs={"check": group_required("Annotator")}),
    path('data/selection/delete_concept/<int:pk>', views.ConceptListView.as_view(), name="delete_concept",
         kwargs={"check": group_required("Annotator")}),
    path("data/sequence_annotation", concept_selected(views.data_import, f"{app_name}:data_concept_selection"),
         name="data_sequence_annotation"),
    path("data/sequence_annotation/query",
         concept_selected(base.views.data_import_query(class_type_id=ConceptClassificationConfig.class_type_id),
                          f"{app_name}:data_concept_selection"),
         name="data_sequence_annotation_query", kwargs={"check": group_required("Annotator")}),
    path("data/webcrawler",
         concept_selected(TemplateView.as_view(template_name='concept_classification/data-web-image-acquisition.html'),
                          f"{app_name}:data_concept_selection"),
         name="data_webcrawler"),
    path("data/webcrawler/query", views.web_search_query, name="data_web_crawler_query",
         kwargs={"check": group_required("Annotator")}),
    path("data/similarity_search",
         concept_selected(views.similarity_search, f"{app_name}:data_concept_selection"),
         name="data_similarity_search"),
    path("data/similarity_search/query", views.similarity_search_query, name="data_similarity_search_query",
         kwargs={"check": group_required("Annotator")}),
    path("data/review_positive",
         concept_selected(views.review(False, True), f"{app_name}:data_concept_selection"),
         name="data_review_positive", kwargs={"check": group_required("Annotator")}),
    path("data/review_neutral",
         concept_selected(views.review(True, False), f"{app_name}:data_concept_selection"),
         name="data_review_neutral", kwargs={"check": group_required("Annotator")}),
    path("data/review_negative",
         concept_selected(views.review(False, False), f"{app_name}:data_concept_selection"),
         name="data_review_negative", kwargs={"check": group_required("Annotator")}),
    path("data/review/query",
         concept_selected(views.review_query, f"{app_name}:data_concept_selection"),
         name="data_review_query", kwargs={"check": group_required("Annotator")}),
    path("model/dataset_overview", views.model_dataset_overview,
         name="model_dataset_overview", kwargs={"check": group_required("Trainer")}),
    path("model/training", TemplateView.as_view(template_name="concept_classification/model-training.html"),
         name="model_training", kwargs={"check": group_required("Trainer")}),
    path("model/evaluation", base.views.model_evaluation(class_type_id=ConceptClassificationConfig.class_type_id),
         name="model_evaluation", kwargs={"check": group_required("Trainer")}),
    path("model/inference", TemplateView.as_view(template_name="concept_classification/model-inference.html"),
         name="model_inference"),
    path("retrieval", views.RetrievalView.as_view(), name="retrieval"),
    path("retrieval/query", base.views.retrieval_query(class_type_id=ConceptClassificationConfig.class_type_id),
         name="retrieval_query", kwargs={"check": group_required("Annotator")}),
    path("export", TemplateView.as_view(template_name="page/export.html"), name="export")
]
