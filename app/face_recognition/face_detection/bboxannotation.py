from django.core.exceptions import ObjectDoesNotExist
from base.models import Bboxannotation, Image, Class, User


def set_image_bbox(image: Image, class_id: int, bbox: dict, user: User):
    """This method writes the given bound box for a specified image to the database.
    :param image: the image
    :param class_id: the class that the image should be annotated for
    :param bbox: the bbox in format {'x': x, 'y': y, 'w': w, 'h': h}
    :param user: the user
    """
    if class_id:
        try:
            b = Bboxannotation.objects.get(classid=Class.objects.get(id=class_id), imageid=image)
            if b.x != bbox['x'] or b.y != bbox['y'] or b.w != bbox['w'] or b.h != bbox['h']:
                b.x = bbox['x']
                b.y = bbox['y']
                b.w = bbox['w']
                b.h = bbox['h']
                b.userid = user
                b.save()
        except ObjectDoesNotExist:
            Bboxannotation.objects.create(classid=Class.objects.get(id=class_id), imageid=image, x=bbox['x'], y=bbox['y'], w=bbox['w'], h=bbox['h'])
    # TODO check if this is needed
    else:
        bbox_set = Bboxannotation.objects.filter(imageid=image)
        bbox_exists = False
        for b in bbox_set:
            if b.x == bbox['x'] and b.y == bbox['y'] and b.w == bbox['w'] and b.h == bbox['h']:
                bbox_exists = True
        if not bbox_exists:
            Bboxannotation.objects.create(classid=None, imageid=image, x=bbox['x'], y=bbox['y'], w=bbox['w'],
                                          h=bbox['h'])


def delete_image_bbox(image: Image, class_id: int, bbox: dict) -> None:
    """Deletes class associated with bounding box for a given image

    :param image: the image
    :param class_id: the class id of the annotation
    :param bbox: the bbox in format {'x': x, 'y': y, 'w': w, 'h': h}
    """
    try:
        b = Bboxannotation.objects.get(imageid=image, classid=Class.objects.get(id=class_id), x=bbox['x'], y=bbox['y'], w=bbox['w'],
                                       h=bbox['h'])
        # TODO case unknown face bboxes are saved to db
        # b.classid = None
        # b.save()
        b.delete()
    except ObjectDoesNotExist:
        pass
