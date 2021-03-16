import datetime
import os

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import resolve, reverse

from viva.jinja2 import generate_menu
from viva.settings import MEDIA_URL, DEBUG, SESSION_COOKIE_AGE, KerasFlaskConfig, PersonTrainInferConfig

CHECK_FUNCTION_KEY = "check"


class AccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # do a check routine if request path does not equal certain special urls
        if request.path not in [reverse("base:start"), reverse("accounts:login"), reverse("accounts:logout"),
                                reverse("accounts:apply_user"), reverse("accounts:blocked"), reverse("favicon")]:

            # general check if user is logged in
            if not request.user.is_authenticated:
                return HttpResponseRedirect(reverse("base:start") + "?next=" + request.path)

            # allow media files for all authenticated users - otherwise do checks
            if request.path.startswith(MEDIA_URL):
                if not DEBUG:
                    response = HttpResponse()
                    # Content-type will be detected by nginx
                    del response['Content-Type']
                    response['X-Accel-Redirect'] = '/protected' + request.path
                    return response
            elif not DEBUG and request.path.startswith(KerasFlaskConfig.Flask.URL + "/"):
                response = HttpResponse()
                del response['Content-Type']  # Content-type will be detected by nginx
                response['X-Accel-Redirect'] = "@internal_flask"
                response['X-Accel-Location'] = request.path[len(KerasFlaskConfig.Flask.URL) + 1:] + (
                    "" if len(request.GET) == 0 else "?" + request.GET.urlencode())
                if response['X-Accel-Location'] == os.environ['FLASK_URL_SSE'][1:]:
                    response['X-Accel-Redirect'] = "@internal_flask_stream"
                return response
            elif not DEBUG and request.path.startswith(PersonTrainInferConfig.URL + "/"):
                response = HttpResponse()
                del response['Content-Type']
                response['X-Accel-Redirect'] = "@internal_hug"
                response['X-Accel-Location'] = request.path[len(PersonTrainInferConfig.URL) + 1:] + (
                    "" if len(request.GET) == 0 else "?" + request.GET.urlencode())
                return response
            else:
                resolved_path = resolve(request.path)

                # if the view function equal to the django RedirectView allow it
                # TODO: Better way of implementing this without invoking the view function?
                # noinspection PyProtectedMember
                if str(resolved_path._func_path) == 'django.views.generic.base.RedirectView':
                    return self.get_response(request)
                # view_func_path = re.findall(r'\(func=([^,]*)', str(resolve(request.path)))[0]
                # if view_func_path == 'django.views.generic.base.RedirectView':
                #     return self.get_response(request)

                # check if this path is specified in a menus.py and if the check_func resolves to True (visible = True)
                menu = generate_menu({"request": request})
                visible_menu_item_found = False
                for _, menu_items in menu["menus"].items():  # iterate over menu of apps
                    if matching_menu_item_visible(menu_items, request.path):
                        visible_menu_item_found = True
                        break

                # if no menu item is defined check if check is provided in urls.py and evaluate
                if not visible_menu_item_found:
                    check_func = resolved_path.kwargs[CHECK_FUNCTION_KEY] \
                        if CHECK_FUNCTION_KEY in resolved_path.kwargs else None
                    if not callable(check_func) or not check_func(request):
                        raise PermissionDenied

        response = self.get_response(request)
        set_session_timeout_cookie(response)

        return response

    # noinspection PyMethodMayBeStatic
    def process_view(self, request, view_func, view_args, view_kwargs):
        if CHECK_FUNCTION_KEY in view_kwargs:
            del view_kwargs[CHECK_FUNCTION_KEY]


def set_session_timeout_cookie(response):
    datetime_now = datetime.datetime.now()  # in container time is set to UTC
    response.set_cookie('session_timeout',
                        int(datetime.datetime.timestamp(
                            datetime_now + datetime.timedelta(seconds=SESSION_COOKIE_AGE + 10))),
                        samesite='Lax')


def matching_menu_item_visible(menu_items, request_path):
    for menu_item in menu_items:
        if menu_item.url == request_path:
            if menu_item.visible:
                return True
            else:
                break
        if menu_item.children:
            if matching_menu_item_visible(menu_item.children, request_path):
                return True
    return False
