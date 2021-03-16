# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = True` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
import json
import math
from typing import Any, Callable, List, Union

from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.db import models
from django.db.models import QuerySet, UniqueConstraint
from django.db.models.signals import post_save
from django.dispatch import receiver

from viva.settings import GridConfig


class GroupDescription(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    description = models.TextField(max_length=500, blank=True)

    class Meta:
        managed = True
        db_table = 'auth_group_description'


@receiver(post_save, sender=Group)
def create_group_description(sender, instance, created, **kwargs):
    if created:
        GroupDescription.objects.create(group=instance)


@receiver(post_save, sender=Group)
def save_group_description(sender, instance, **kwargs):
    instance.groupdescription.save()


class Collection(models.Model):
    id = models.BigAutoField(primary_key=True)
    basepath = models.CharField(unique=True, max_length=300)
    description = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255)

    class Meta:
        managed = True
        db_table = 'collection'


class Class(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)
    classtypeid = models.ForeignKey('Classtype', models.PROTECT, db_column='classtypeid', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'class'


class Classtype(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'classtype'


class Evaluation(models.Model):
    id = models.BigAutoField(primary_key=True)
    precision = models.FloatField()
    classid = models.ForeignKey(Class, models.PROTECT, db_column='classid')
    modelid = models.ForeignKey('Model', models.PROTECT, db_column='modelid')

    class Meta:
        managed = True
        db_table = 'evaluation'
        unique_together = (('modelid', 'classid'),)


class Image(models.Model):
    id = models.BigAutoField(primary_key=True)
    path = models.ImageField(max_length=270, unique=True)
    collectionid = models.ForeignKey(Collection, models.PROTECT, db_column='collectionid')

    class Meta:
        managed = True
        db_table = 'image'


class Imageannotation(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateTimeField(auto_now=True)
    difficult = models.BooleanField()
    groundtruth = models.BooleanField()
    classid = models.ForeignKey(Class, models.PROTECT, db_column='classid')
    imageid = models.ForeignKey(Image, models.PROTECT, db_column='imageid')
    userid = models.ForeignKey(User, models.PROTECT, db_column='userid', null=True)

    class Meta:
        managed = True
        db_table = 'imageannotation'
        unique_together = (('imageid', 'classid'),)


class Bboxannotation(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateTimeField(auto_now=True)
    imageid = models.ForeignKey(Image, models.PROTECT, db_column='imageid')
    classid = models.ForeignKey(Class, models.PROTECT, db_column='classid', null=True)
    userid = models.ForeignKey(User, models.PROTECT, db_column='userid', null=True)
    x = models.IntegerField()
    y = models.IntegerField()
    w = models.IntegerField()
    h = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'bboxannotation'
        constraints = [
            UniqueConstraint(fields=['imageid', 'classid'],
                             name='unique_with_classid'),
        ]


class Imageprediction(models.Model):
    id = models.BigAutoField(primary_key=True)
    score = models.FloatField()
    classid = models.ForeignKey(Class, models.PROTECT, db_column='classid')
    imageid = models.ForeignKey(Image, models.PROTECT, db_column='imageid')
    modelid = models.ForeignKey('Model', models.PROTECT, db_column='modelid')

    class Meta:
        managed = True
        db_table = 'imageprediction'
        unique_together = (('imageid', 'classid', 'modelid'),)


class Imageurl(models.Model):
    imageid = models.OneToOneField(Image, models.PROTECT, db_column='imageid', primary_key=True)
    url = models.CharField(max_length=300)
    downloaded = models.BooleanField(default=False)
    error = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = 'imageurl'


class Model(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateTimeField(unique=True)
    dir_name = models.CharField(unique=True, max_length=20)
    inference_stored = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = 'model'


class Video(models.Model):
    id = models.BigAutoField(primary_key=True)
    path = models.CharField(max_length=300, unique=True)

    class Meta:
        managed = True
        db_table = 'video'


class Videoframe(models.Model):
    id = models.BigAutoField(primary_key=True)
    number = models.IntegerField()
    videoid = models.ForeignKey(Video, models.PROTECT, db_column='videoid')
    imageid = models.ForeignKey(Image, models.PROTECT, db_column='imageid')
    shotid = models.ForeignKey('Videoshot', models.PROTECT, db_column='shotid')

    class Meta:
        managed = True
        db_table = 'videoframe'
        unique_together = (('number', 'videoid'),)


class Videoshot(models.Model):
    id = models.BigAutoField(primary_key=True)
    startframe = models.IntegerField()
    endframe = models.IntegerField()
    videoid = models.ForeignKey(Video, models.PROTECT, db_column='videoid')

    class Meta:
        managed = True
        db_table = 'videoshot'
        unique_together = (('startframe', 'videoid'),)


def serialize_images(query: Union[QuerySet, List], request: WSGIRequest,
                     image_extractor: Callable[[Any], Image] = lambda x: x,
                     additional_value_function: Callable[[dict, Image], None] = None,
                     return_dict: bool = False) -> Union[dict, str]:
    """Serialize a given QuerySet or List resulting in a JSON object that contains all required information about
    the contained images to build a grid (or maybe other elements in future too). If the QuerySet/List is not based on
    Image.objects then provide a function (image_extractor) that extracts the Image object form a given object of the
    QuerySet/List. If needed additional values can be added to the every JSON object corresponding to an element by
    specifying another function (additional_value_function) which can modify the dictionary for the element handed over
    by parameter.

    JSON object specification:

    ========  ==========  ==============================================================================================
    key       value       notes
    ========  ==========  ==============================================================================================
    elements  JSON array  Array containing objects representing an image object of the database.

                          ==============  ===========  =================================================================
                          key             value        notes
                          ==============  ===========  =================================================================
                          id              int          the database id of the image
                          url             string       the url of the image on this server
                          media_type      string       'image' or 'video'
                          download_url    string       (optional) the download url of the image
                          downloaded      string       (optional) indicates if the image has been downloaded
                          download_error  string       (optional) indicates if there has been an error downloading this
                                                       image
                          video           JSON object  (required if 'media_type' is 'video') if there is an associated
                                                       video for this image.
                                                       JSON object defining associated video attributes

                                                       ==========  ======  =============================================
                                                       key         value   notes
                                                       ==========  ======  =============================================
                                                       url         string  the url of the video on this server
                                                       startframe  int     the number of the start marking the start of
                                                                           shot where the image appeared
                                                       endframe    int     the number of the frame marking the end
                                                       ==========  ======  =============================================

                          annotation      JSON object  (optional) if there is an annotation for the image.
                                                       JSON object specifying the associated annotation

                                                       ===========  =====  =============================================
                                                       key          value  notes
                                                       ===========  =====  =============================================
                                                       difficult    bool   is the annotation difficult
                                                       groundtruth  bool   if annotation is not difficult the label type
                                                       ===========  =====  =============================================

                          ...             ...          Additional values added by providing 'additional_value_function'
                          ==============  ===========  =================================================================

    count     int         Total amount of elements for this query
    ========  ==========  ==============================================================================================

    :param query: The QuerySet of the database query or a List
    :param request: The web request issued by an user
    :param image_extractor: Optional function to get the instance of Image for every object in QuerySet
    :param additional_value_function: Optional function to add additional values to JSON object of every element
    :param return_dict: Optionally return a dictionary instead of a string (to add additional values)
    :return: The string representation of the serialized images in JSON format or the dictionary of the serialized
             images
    """
    json_arr = {'elements': [], 'count': query.count() if isinstance(query, QuerySet) else len(query)}
    annotating_class = Class.objects.get(id=int(request.POST[GridConfig.PARAMETER_ANNOTATION_CLASS])) \
        if GridConfig.PARAMETER_ANNOTATION_CLASS in request.POST else None
    if isinstance(query, QuerySet):  # apply pagination on QuerySet
        page_elements = Paginator(query, int(request.POST[GridConfig.PARAMETER_ELEMENT_COUNT])) \
            .page(int(request.POST[GridConfig.PARAMETER_PAGE]))
    else:
        page_elements = query
    for query_obj in page_elements:
        image = image_extractor(query_obj)
        image_obj = {
            'id': image.id,
            'url': image.path.url,
            'media_type': 'image'
        }
        try:
            image_url = image.imageurl
            image_obj.update({
                'download_url': image_url.url,
                'downloaded': image_url.downloaded,
                'download_error': image_url.error
            })
        except ObjectDoesNotExist:
            pass
        if image.videoframe_set.exists():
            image_obj.update({
                'media_type': 'video',
                'video': {
                    'url': image.videoframe_set.first().videoid.path,
                    'startframe': math.floor(image.videoframe_set.first().shotid.startframe / 25),
                    'endframe': math.ceil(image.videoframe_set.first().shotid.endframe / 25)
                }
            })
        if annotating_class and image.imageannotation_set.filter(classid=annotating_class).exists():
            image_obj.update({
                'annotation': {
                    'difficult': image.imageannotation_set.filter(classid=annotating_class).first().difficult,
                    'groundtruth': image.imageannotation_set.filter(classid=annotating_class).first().groundtruth
                }
            })
        if additional_value_function:
            additional_value_function(image_obj, image)
        json_arr['elements'].append(image_obj)
    return json_arr if return_dict else json.dumps(json_arr)
