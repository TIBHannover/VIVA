"""concept_classification URL Configuration

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
from django.contrib.auth import views as auth_views
from django.urls import path

from base import views
from base.tools.checks import is_user_authenticated, group_required

app_name = "base"
urlpatterns = [
    path('', auth_views.LoginView.as_view(), name='start'),
    path('api/save_grid_annotations', views.save_grid_annotations,
         name='save-grid-annotations', kwargs={"check": is_user_authenticated()}),
    path("export/file", views.export_file, name="export_file", kwargs={"check": group_required("Annotator")})
]
