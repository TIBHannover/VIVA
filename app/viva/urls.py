"""viva URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.shortcuts import render_to_response
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from concept_classification.apps import ConceptClassificationConfig
from face_recognition.apps import FaceRecognitionConfig
from viva import settings

urlpatterns = [
    path('', include('base.urls')),
    path('accounts/', include('accounts.urls')),
    path(f"{ConceptClassificationConfig.short_name}/", include('concept_classification.urls')),
    path(f"{FaceRecognitionConfig.short_name}/", include('face_recognition.urls')),
    re_path(r'^favicon\.ico$', RedirectView.as_view(url='/static/images/favicon.ico'), name="favicon"),
    path('django-rq/', include('django_rq.urls'))
]


def handler500(request):
    response = render_to_response("500.html")
    response.status_code = 500
    return response


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
