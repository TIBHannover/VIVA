import functools

from django.http import HttpResponseRedirect
from django.urls import reverse

from viva.settings import SessionConfig


def concept_selected(func, redirect_url_name):
    """Checks whether the required session variable is available
    - if not redirect to provided url - a get parameter is added to pass the original request url
    :param func: the request view function
    :param redirect_url_name: the url name to redirect to if condition of set variable is not met
    :return: a function that wraps around the original view function
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if SessionConfig.SELECTED_CONCEPT_SESSION_KEY in request.session:
            return func(request, *args, **kwargs)
        return HttpResponseRedirect(reverse(redirect_url_name) + "?next=" + request.path)

    return wrapper


def person_selected(func, redirect_url_name):
    """Checks whether the required session variable is available
    - if not redirect to provided url - a get parameter is added to pass the original request url
    :param func: the request view function
    :param redirect_url_name: the url name to redirect to if condition of set variable is not met
    :return: a function that wraps around the original view function
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if SessionConfig.SELECTED_PERSON_SESSION_KEY in request.session:
            return func(request, *args, **kwargs)
        return HttpResponseRedirect(reverse(redirect_url_name) + "?next=" + request.path)

    return wrapper
