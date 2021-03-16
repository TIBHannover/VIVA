import imghdr
import json
import time
from enum import Enum, auto
from string import Template
from typing import Union

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.utils.datastructures import MultiValueDictKeyError

from base.models import Image
from concept_classification.similarity_search.errors import *
from viva.settings import EsConfig as Cfg
from .monkeypatch_imghdr import monkeypatch_imghdr


class SearchMode(Enum):
    UPLOAD = auto()
    URL = auto()
    DB_IMAGE = auto()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Cfg.WS_ALLOWED_EXT


def parse_el_results(json_str):
    """
    Parse ES results to image dicts (image_id, score, hit_id)
    :param json_str: JSON formatted string
    :return: list of dicts
    """
    json_result = json.loads(json_str)
    hits = json_result["hits"]["hits"]
    images = []
    for h in hits:
        try:
            image_id = Image.objects.get(path="dra_keyframes/images/" + h["_source"]["imagepath"])
        except ObjectDoesNotExist:
            print("WARNING: EL result contains keyframe not resident in database: "
                  "dra_keyframes/images/" + h["_source"]["imagepath"] + ". Skipping this result.")
            continue
        images.append(image_id)
    return images


def get_hashcodes(img):
    """
    Send image to hashcode webservice and return JSON with hashcodes
    :param img: bytes object of image
    :return: JSON object
    """
    data_dict = {"qi.jpg": img}
    r = requests.post(Cfg.HC_URL, files=data_dict, headers=Cfg.HC_CLIENT_HEADER)
    return json.loads(r.text)["results"][0]["codes"]


def get_el_results(img, max_results):
    """
    Get hashcodes for image, parse codes, send codes to ES
    :param img: bytes object of image
    :param max_results: maximum number of results to retrieve from ES
    :return: Response object
    """
    code_dict = get_hashcodes(img)
    s = Template(Cfg.EL_QUERY_TPL)
    el_query = s.substitute(**code_dict)
    return requests.post(Cfg.ES_URL + str(max_results), data=el_query, headers={"Content-Type": "application/json"},
                         verify=False).text


def search(mode: SearchMode, mode_obj: Union[File, str, int], max_results: int):
    images = []
    error = None
    query_time = -1
    imghdr.tests.extend(monkeypatch_imghdr())
    try:
        img = None
        if mode is SearchMode.UPLOAD:
            # Query image uploaded
            try:
                file = mode_obj
            except MultiValueDictKeyError:
                raise NoFileUploadedError()
            if not file:
                raise NoFileUploadedError()
            if not allowed_file(file.name):
                raise FileTypeNotAcceptedError()
            else:
                try:
                    img = file.read()
                except:
                    raise CouldNotReadFileError()
        elif mode is SearchMode.URL:
            # Query image from URL
            if mode_obj == "":
                raise NoURLError()
            else:
                try:
                    r = requests.get(mode_obj, stream=True)
                    img = r.content
                except:
                    raise InvalidURLError()
        elif mode is SearchMode.DB_IMAGE:
            # Query fs image
            try:
                file = Image.objects.get(id=mode_obj).path
                img = file.read()
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

        start = time.time()
        try:
            res = get_el_results(img, max_results)
        except:
            raise NoELResultError()
        try:
            images = parse_el_results(res)
        except:
            raise ELParsingError()
        query_time = time.time() - start

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
    except ELParsingError:
        error = "Could not parse EL results"
    except NoELResultError:
        error = "No EL results"
    except FormDataError:
        error = "Error in form data"
    except NoImageFileError:
        error = "Not a valid image file"
    except NoImageSelectedError:
        error = "No image selected"
    except CouldNotFindFileError:
        error = "Image not in database"

    return {"images": images, "error": error, "time": query_time}
