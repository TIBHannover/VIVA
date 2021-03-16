from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.core.handlers.wsgi import WSGIRequest
from django.db import IntegrityError
from django.utils.crypto import get_random_string

from base.models import Collection, Image, Imageannotation, Class, Imageurl
from viva.settings import DB_CRAWLER_COLLECTION_ID


def create_new_web_image(url: str) -> Imageurl:
    """Creates a database entry for a new web image

    :param url: the url for the
    :return: the new Imageurl object
    """
    while True:
        try:
            collection_id = Collection.objects.get(id=DB_CRAWLER_COLLECTION_ID)
            image = Image.objects.create(path=get_random_string(length=32),
                                         collectionid=collection_id)
            break
        except IntegrityError as e:
            print("WARNING: Integrity error for URL " + url + '\n\t' + str(e))
    return Imageurl.objects.create(imageid=image, url=url)


def set_image_annotation(image: Image, class_id: int, difficult: bool, groundtruth: bool, request: WSGIRequest):
    """This method writes the given annotation for a specified image to the database.
    :param image: the image to annotate
    :param class_id: the class that the image should be annotated for
    :param difficult: if the image was difficult to annotate
    :param groundtruth: the label of the image - ignored if difficult
    :param request: the request
    """
    user = request.user
    try:
        ica = Imageannotation.objects.get(imageid=image, classid=class_id)
        if ica.difficult != difficult or ica.groundtruth != groundtruth:
            ica.difficult = difficult
            ica.groundtruth = False if difficult else groundtruth
            ica.date = datetime.now()
            ica.userid = user
            ica.save()
    except ObjectDoesNotExist:
        Imageannotation.objects.create(difficult=difficult, groundtruth=groundtruth, userid=user,
                                       classid=Class.objects.get(id=class_id), imageid=image)


def delete_image_annotation(image: Image, class_id: int) -> None:
    """Deletes a annotation for a given image and class

    :param image: the image
    :param class_id: the class id of the annotation
    """
    try:
        ica = Imageannotation.objects.get(imageid=image, classid=class_id)
        ica.delete()
    except ObjectDoesNotExist:
        pass
