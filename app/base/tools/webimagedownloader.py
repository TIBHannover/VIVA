import os
import shutil
import ssl
import urllib.request
from urllib.parse import urlparse

import PIL
import django_rq
from django.core.handlers.wsgi import WSGIRequest

from base.models import Collection, Imageannotation, Imageurl
from viva.settings import DB_CRAWLER_COLLECTION_ID, MEDIA_ROOT

TMP_DIR = "/tmp/viva"


def add_image_to_download_queue(image_url: Imageurl, request: WSGIRequest):
    """Adds an Imageurl object to the download queue

    :param image_url: the Imageurl object
    :param request: the request for storing it
    """
    queue = django_rq.get_queue('image_downloader')
    queue.enqueue(download_image, image_url, request.session.session_key)


def remove_transparency(im, bg_colour=(255, 255, 255)):
    """This method removes transparent background from a given image.
    :param im: the image to process
    :param bg_colour: the desired background colour, defaulting to 'white'
    :return bg: if the image had a transparent background, the image is returned with a non-transparent
    :return im: if the image did not have a transparent background, the image itself is returned
    """
    # Only process if image has transparency (http://stackoverflow.com/a/1963146)
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
        # Need to convert to RGBA if LA format due to a bug in PIL (http://stackoverflow.com/a/1963146)
        alpha = im.convert('RGBA').split()[-1]
        # Create a new background image of our matt color.
        # Must be RGBA because paste requires both images have the same format
        # (http://stackoverflow.com/a/8720632  and  http://stackoverflow.com/a/9459208)
        bg = PIL.Image.new("RGBA", im.size, bg_colour + (255,))
        bg.paste(im, mask=alpha)
        return bg
    else:
        return im


def download_image(db_img_url: Imageurl, session_id):
    """This method downloads the image under the given URI (and removes possible transparency).
    :param db_img_url: the corresponding Imageurl model object
    :param session_id: the current session's ID (needed to find the image in tmp directory)
    :return tmp_file_path: the image's location on disk
    """
    parsed_url = urlparse(db_img_url.url)
    file_name = os.path.basename(parsed_url.path)
    file_path = os.path.join(TMP_DIR, session_id, file_name)
    try:
        os.makedirs(os.path.join(TMP_DIR, session_id), exist_ok=True)
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent',
                              'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0')]
        urllib.request.install_opener(opener)
        # noinspection PyProtectedMember
        ssl._create_default_https_context = ssl._create_unverified_context
        urllib.request.urlretrieve(db_img_url.url, file_path)
        img = remove_transparency(PIL.Image.open(file_path))
        collection_path = Collection.objects.get(id=DB_CRAWLER_COLLECTION_ID).basepath
        download_path = os.path.join(MEDIA_ROOT, collection_path)
        os.makedirs(download_path, exist_ok=True)
        img_name = str(db_img_url.imageid.id) + '.png'
        img.save(os.path.join(MEDIA_ROOT, collection_path, img_name), 'png', optimize=True, quality=100)
        db_img_url.imageid.path.name = collection_path + "/" + img_name
        db_img_url.downloaded = True
        db_img_url.error = False
        db_img_url.save()
        db_img_url.imageid.save()
    except Exception as e:
        db_img_url.error = True
        db_img_url.save()
        Imageannotation.objects.get(imageid=db_img_url.imageid).delete()
        raise e
    finally:
        shutil.rmtree(os.path.join(TMP_DIR, session_id))
