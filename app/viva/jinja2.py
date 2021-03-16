import json
import math
import os
import re
import sys
from json import JSONDecodeError
from math import ceil

import jinja2
from django.apps import apps
from django.contrib.auth.models import Group, User
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.urls import reverse
from django_jinja import library
from jinja2 import Environment, contextfunction
from menu.templatetags.menu import MenuNode

from base.models import Imageannotation, Class, Bboxannotation
from concept_classification.apps import ConceptClassificationConfig
from face_recognition.apps import FaceRecognitionConfig
from viva.settings import ANNOUNCEMENTS_FILE_PATH, DEBUG, GridConfig, LOGIN_URL, SESSION_COOKIE_AGE, SessionConfig, \
    KerasFlaskConfig, PersonTrainInferConfig, \
    UPLOAD_LIMIT, VERSION_INFO_FILE_PATH, AsyncActionConfig


def environment(**options):
    env = Environment(**options, trim_blocks=True, lstrip_blocks=True)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
        'UPLOAD_LIMIT': UPLOAD_LIMIT,
        'SESSION_TIMEOUT': SESSION_COOKIE_AGE,
        'LOGIN_URL': LOGIN_URL,
        'ACCOUNTS_LOGIN_URL': reverse("accounts:login"),
        'KerasFlaskConfig': KerasFlaskConfig,
        'PersonTrainInferConfig': PersonTrainInferConfig,
        'GridConfig': GridConfig,
        'AsyncActionConfig': AsyncActionConfig
    })
    return env


@library.global_function
def url_replace(request, field, value):
    """This method replaces the specified field in the current URI by the given value.
    :parameter request the request
    :parameter field the URIs field to be replaced
    :parameter value the value to be set
    :return the updated URI
    """
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()


@library.global_function
def list_apps():
    """This method lists all displayable apps of the current project.
    :return list_of_apps the apps
    """
    list_of_apps = []
    for app in apps.get_app_configs():
        try:
            if app.show_start_page:
                list_of_apps.append(app)
        except AttributeError:
            pass
    return list_of_apps


@library.global_function
def is_child_menu_item_selected(menu_item):
    """Returns whether a child item of a menu item is selected or not (to display open menu)
    :param menu_item:
    :return:
    """
    for child_item in menu_item.children:
        if len(child_item.children) > 0:
            return any([grand_child.selected for grand_child in child_item.children])
        if child_item.selected:
            return True
    return False


@library.global_function
def get_groups_as_string(groups):
    """This method converts a list of groups into a string.
    :parameter groups the groups to be converted
    :return the given groups converted into a string
    """
    group_str = ""
    for group in groups:
        group_str += group.name + ", "
    return "" if len(group_str) == 0 else group_str[:-2]


@library.global_function
def grid_parameters(request, grid_elements):
    """This method pastes together all parameters needed by the data grid
    :parameter request the request
    :parameter grid_elements the elements to be shown in the grid
    :return a dict containing all parameters needed by the data grid (elements, page, cols, rows, pagecount)
    """
    page = int(request.POST["pageNum"])
    cols = min(int(request.COOKIES.get('grid_cols')), 20)  # default defined in "static/base/js/grid.js"
    rows = min(int(request.COOKIES.get('grid_rows')), 20)
    elements = grid_elements[cols * rows * (page - 1):cols * rows * page]
    page_count = int(ceil(len(grid_elements) / (cols * rows)))
    return {'elements': elements, 'page': page, 'cols': cols, 'rows': rows, 'page_count': page_count,
            'post_url': request.path, 'grid_elements': grid_elements, 'grid_id': request.POST['gridId']}


@library.global_function
@contextfunction
def generate_menu(context):
    """This method is a wrapper for generate_menu of django-simple-menu
    :parameter context the context
    :return menu_dict the information needed provided by django-simple-menu's generate_menu function
    """
    menu = MenuNode()
    menu_dict = {"request": context["request"]}
    menu.render(menu_dict)
    menu_dict.pop("request")
    return menu_dict


@library.global_function
def get_app_version_information():
    version_dict = {}
    if not DEBUG and os.path.isfile(VERSION_INFO_FILE_PATH):
        with open(VERSION_INFO_FILE_PATH) as f:
            version_content = f.readlines()
        version_dict["commit_hash"] = version_content[0].strip()
        version_dict["commit_title"] = version_content[1].strip()
        version_dict["commit_author"] = version_content[2].strip()
        version_dict["commit_time"] = version_content[3].strip()
        if len(version_content) == 5:
            version_dict["tag_name"] = version_content[4].strip()
    return version_dict


@library.global_function
def is_user_in_group(user: User, groupid):
    return user.groups.filter(id=groupid).exists()


@library.global_function
def get_group_description(group: Group):
    return group.groupdescription.description


@library.global_function
def sizeof_fmt(size, suffix='B'):
    """Return a human-readable string representation of a file's size
    This method was copied from NVIDIA DIGITS repository
    https://github.com/NVIDIA/DIGITS/blob/7a3d5f00f3ef0e81cdc3415b03c6ede98c3ef91c/digits/utils/__init__.py#L109

    :param size: size in bytes
    :param suffix:
    :return: human-readable string representation of the size
    """
    try:
        size = int(size)
    except ValueError:
        return None
    if size <= 0:
        return '0 %s' % suffix

    size_name = ('', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    i = int(math.floor(math.log(size, 1024)))
    if i >= len(size_name):
        i = len(size_name) - 1
    p = math.pow(1024, i)
    s = size / p
    # round to 3 significant digits
    s = round(s, 2 - int(math.floor(math.log10(s))))
    if s.is_integer():
        s = int(s)
    if s > 0:
        return '%s %s%s' % (s, size_name[i], suffix)
    else:
        return '0 %s' % suffix


@library.global_function
def is_macro(expression):
    return type(expression) == jinja2.runtime.Macro


@library.global_function
@contextfunction
def get_annotating_class_id(context):
    request = context['request']
    if request.resolver_match.app_name == ConceptClassificationConfig.name and \
            SessionConfig.SELECTED_CONCEPT_SESSION_KEY in request.session:
        class_id = request.session[SessionConfig.SELECTED_CONCEPT_SESSION_KEY]
    elif SessionConfig.SELECTED_PERSON_SESSION_KEY in request.session \
            and request.resolver_match.app_name == FaceRecognitionConfig.name:
        class_id = request.session[SessionConfig.SELECTED_PERSON_SESSION_KEY]
    else:
        return None
    return class_id


@library.global_function
def count_class_images(classes, class_type_id):
    """This method determines the number of images per annotation class for the given concepts.
    :return the number of positive, negative and neutral images for each concept
    """
    annotations = Imageannotation.objects.filter(
        classid__classtypeid=class_type_id, classid__in=classes).values('classid')
    positives = annotations.filter(groundtruth=True, difficult=False).annotate(count=Count('classid'))
    negatives = annotations.filter(groundtruth=False, difficult=False).annotate(count=Count('classid'))
    neutrals = annotations.filter(difficult=True).annotate(count=Count('classid'))
    return [dict(positives.values_list('classid', 'count')), dict(negatives.values_list('classid', 'count')),
            dict(neutrals.values_list('classid', 'count'))]


@library.global_function
def count_class_bboxes(classes):
    """This method determines the number of annotated bboxes for the given persons.
    :return the number of positive bboxes for each person
    """
    annotations = Bboxannotation.objects.filter(classid__in=classes).values('classid').annotate(count=Count('classid'))
    return dict(annotations.values_list('classid', 'count'))


@library.global_function
def get_class_ids(class_type):
    """Get all class IDs corresponding to the specified class type

    :param class_type: the class type
    :return: the class IDs
    """
    result = Class.objects.filter(classtypeid=class_type).values_list('id', flat=True)
    return list(result)


@library.global_function
@contextfunction
def get_selected_class(context) -> str:
    """Get the active app's currently selected class

    :param context: the context
    :return: the selected class's name
    """
    class_id = get_annotating_class_id(context)
    if class_id is None:
        return ""
    try:
        class_name = Class.objects.get(id=class_id).name
    except ObjectDoesNotExist:
        class_name = ""
    return class_name


@library.global_function
@contextfunction
def get_selected_class_search_term(context) -> str:
    """Get a simplified search term for the current selected class (used in webcrawler)

    :param context: the context
    :return: search term for current selected class name
    """
    return re.sub(r"\([^)]+\)", "", get_selected_class(context).replace('/', ' ').replace(',', ''))


@library.global_function
def get_announcements():
    announcements = []
    if not DEBUG and os.path.isfile(ANNOUNCEMENTS_FILE_PATH):
        with open(ANNOUNCEMENTS_FILE_PATH) as f:
            try:
                announcements = json.load(f)
            except JSONDecodeError as e:
                print("Invalid announcements file: Could not parse JSON content!", file=sys.stderr)
                print(e, file=sys.stderr)
    return announcements


@library.global_function
@contextfunction
def get_export_default_threshold(context) -> int:
    if context['request'].resolver_match.app_name == ConceptClassificationConfig.name:
        return int(os.environ['EXPORT_DEFAULT_THRESHOLD_CC'])
    return int(os.environ['EXPORT_DEFAULT_THRESHOLD_FR'])
