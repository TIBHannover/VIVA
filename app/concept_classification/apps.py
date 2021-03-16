import os

from django.apps import AppConfig


class ConceptClassificationConfig(AppConfig):
    name = os.environ['DJANGO_APP_NAME_CONCEPT']
    short_name = "cc"

    show_start_page = True
    title = "Concepts"
    description = "Create and train models to classify specified concepts."
    text = "Start"
    link = f"/{short_name}"
    icon = "fa-images"
    class_type_id = int(os.environ['DB_CLTP_ID_CONCEPT'])
