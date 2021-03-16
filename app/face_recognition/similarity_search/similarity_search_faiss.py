import requests
import base64
from concept_classification.similarity_search.monkeypatch_imghdr import monkeypatch_imghdr
from .errors import *
import imghdr
import time
from django.core.exceptions import ObjectDoesNotExist
from django.utils.datastructures import MultiValueDictKeyError
from viva.settings import EsConfig as Cfg, PersonTrainInferConfig
import json

from base.models import Image, Bboxannotation, Imageurl


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Cfg.WS_ALLOWED_EXT


def similarity_search_handle_request(request):
    images = []
    max_results = None
    error = ""
    query_time = 0
    perform_search = False
    bbox_string = " "
    # add jpeg to imhdr test
    imghdr.tests.extend(monkeypatch_imghdr())

    try:
        # Query image from results
        if request.method == 'GET':
            if "imagePath" in request.GET.keys():
                try:
                    image_path = request.GET["imagePath"]
                    max_results = request.GET["maxResults"]
                except:
                    raise FormDataError()
                try:
                    max_results = int(max_results)
                except:
                    raise MaxResultsNoNumberError()
                try:
                    url = Cfg.WS_IMAGES_URL + "/" + image_path
                    r = requests.get(url, stream=True, verify=False)
                    img = r.content
                    perform_search = True
                except:
                    raise InvalidURLError()
                try:
                    ext = imghdr.what("", h=img)
                except:
                    raise NoImageFileError()

        if request.method == 'POST':
            perform_search = True
            try:
                mode = request.POST["mode"]
                url = request.POST["url"]
                max_results = request.POST["max"]
            except:
                raise FormDataError
            try:
                max_results = int(max_results)
            except:
                raise MaxResultsNoNumberError()
            # Query image from URL
            if mode == "url":
                if url == "":
                    raise NoURLError()
                else:
                    try:
                        r = requests.get(url, stream=True)
                        img = r.content
                    except:
                        raise InvalidURLError()
            elif mode == "upload":
                # Query image uploaded
                try:
                    file = request.FILES["file"]
                except MultiValueDictKeyError:
                    raise NoFileUploadedError
                if not file:
                    raise NoFileUploadedError()
                if not allowed_file(file.name):
                    raise FileTypeNotAcceptedError()
                else:
                    try:
                        img = file.read()
                    except:
                        raise CouldNotReadFileError()
            elif mode == "select":
                # Query fs image
                try:
                    image = Image.objects.get(id=int(request.POST["select"]))

                    if Imageurl.objects.filter(imageid=image).exists():
                        url = Imageurl.objects.get(imageid=image).url
                        r = requests.get(url, stream=True)
                        img = r.content
                    else:
                        file = image.path
                        img = file.read()
                    try:
                        bbox_obj = Bboxannotation.objects.get(imageid_id=int(request.POST["select"]),
                                                              classid_id=int(request.POST['annotation_class']))
                        bbox_string = f"{bbox_obj.x} {bbox_obj.y} {bbox_obj.w} {bbox_obj.h}"
                    except ObjectDoesNotExist:
                        pass

                except ValueError:
                    raise NoImageSelectedError()
                except ObjectDoesNotExist:
                    raise CouldNotFindFileError()
                except (IOError, OSError):
                    raise CouldNotReadFileError()
            try:
                ext = imghdr.what("", h=img)
            except:
                raise NoImageFileError()
            if ext is None:
                raise NoImageFileError()

        if perform_search:
            start = time.time()

            img_enc = base64.b64encode(img)
            ext = 'jpg'
            body = {
                'img': img_enc,
                'filetype': ext,
                'max_results': max_results,
                'query_bbox': bbox_string
            }
            response = json.loads(requests.post(PersonTrainInferConfig.URL_ALIAS + "/similarity_search", body).text)
            error = response['error']

            bboxes = []
            images = []
            if not error:
                for result in response['paths']:
                    try:
                        image = Image.objects.get(path=result['path'])
                        images.append(image)
                        bboxes.append(result['bbox'])
                    except ObjectDoesNotExist:
                        pass
            query_time = time.time() - start

    except MaxResultsNoNumberError:
        error = "Maximum results is not a number"
    except NoURLError:
        error = "No URL entered"
    except InvalidURLError:
        error = "Invalid URL"
    except FileTypeNotAcceptedError:
        error = "File type not accepted"
    except CouldNotReadFileError:
        error = "Could not read file"
    except NoFileUploadedError:
        error = "No file uploaded"
    except FormDataError:
        error = "Error in form data"
    except NoImageFileError:
        error = "Not a valid image file"
    except NoImageSelectedError:
        error = "No image selected"
    except CouldNotFindFileError:
        error = "Image not in database"

    return {"images": images, "bbox_check_list": bboxes, "error": error, "time": query_time}
