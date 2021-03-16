from django.core.exceptions import ObjectDoesNotExist

from base.models import Imageprediction, Image, Class, Model, Evaluation
from face_recognition.apps import FaceRecognitionConfig


def set_image_prediction(image: Image, image_class: Class, model: Model, score: float):
    """
    Updates the image prediction for the given image, class and model if it exists. Otherwise create the object.
    :param image:
    :param image_class:
    :param model:
    :param score:
    :return:
    """

    def truncate(n, decimals=0):
        multiplier = 10 ** decimals
        return int(n * multiplier) / multiplier

    score = truncate(score, 6)

    try:
        image_prediction = Imageprediction.objects.get(imageid=image, classid=image_class, modelid=model)

        if image_prediction.score > score:
            image_prediction.score = score
            image_prediction.save()
    except ObjectDoesNotExist:
        Imageprediction.objects.create(imageid=image, classid=image_class, modelid=model, score=score)


def delete_image_prediction(image: Image, image_class: Class, model: Model) -> None:
    """
    Deletes an image_prediction for a given image, class and model
    :param image:
    :param image_class:
    :param model:
    :return:
    """
    try:
        image_prediction = Imageprediction.objects.get(imageid=image, classid=image_class, modelid=model)
        image_prediction.delete()
    except ObjectDoesNotExist:
        pass


def delete_previous_model_predictions(n: int) -> None:
    """
    Deletes all stored image model predictions and models excluding last n models
    :param n: last n models to keep
    :return:
    """
    # evaluation_person = Class.objects.filter(classtypeid_id=FaceRecognitionConfig.class_type_id).values_list('evaluation', flat=True)
    evaluation_person = Evaluation.objects.filter(
        classid__classtypeid_id=FaceRecognitionConfig.class_type_id).values_list('id', flat=True)
    if evaluation_person.exists():
        modelids_to_delete = Model.objects.filter(evaluation__in=evaluation_person). \
                                 values_list('id', flat=True).distinct().order_by('-id')[n:]
        if modelids_to_delete.exists():
            Imageprediction.objects.filter(modelid__in=modelids_to_delete).delete()
            Evaluation.objects.filter(modelid__in=modelids_to_delete).delete()
            Model.objects.filter(id__in=modelids_to_delete).delete()
            # TODO delete actual model from model path


def set_model_inference_stored(modelid: int) -> None:
    """
    Sets inference_stored true for given model
    :param modelid: id of given model
    :return:
    """
    try:
        model = Model.objects.get(id=modelid)
        model.inference_stored = True
        model.save()
    except ObjectDoesNotExist:
        pass
