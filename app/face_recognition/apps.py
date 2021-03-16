import os

from django.apps import AppConfig


class FaceRecognitionConfig(AppConfig):
    name = os.environ['DJANGO_APP_NAME_PERSON']
    short_name = "fr"

    show_start_page = True
    title = "Persons"
    description = "Create and train models to classify faces."
    text = "Start"
    link = f"/{short_name}"
    icon = "fa-users"
    class_type_id = int(os.environ['DB_CLTP_ID_PERSON'])
