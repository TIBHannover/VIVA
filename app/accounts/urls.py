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
from django.urls import include, path

from accounts.apps import AccountsConfig
from base.tools.checks import group_required
from . import views

app_name = AccountsConfig.name
urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('profile/', views.UserUpdateView.as_view(), name='profile'),
    path('apply_user/', views.UserApplyView.as_view(), name='apply_user'),
    path('blocked/', views.get_blocked_page, name='blocked'),
    path('change_password/', views.ChangeUserPasswordView.as_view(), name='change_password'),
    path('um/create_user/', views.UserCreateView.as_view(), name='create_user'),
    path('um/user_list/', views.UserListView.as_view(), name='user_list'),
    path('um/edit_user/<int:pk>', views.UserEditView.as_view(), name='edit_user',
         kwargs={"check": group_required("User manager")}),
    path('um/delete_user/<int:pk>', views.UserDeleteView.as_view(), name='delete_user',
         kwargs={"check": group_required("User manager")}),
    path('um/set_password/', views.set_user_password, name='set_user_password',
         kwargs={"check": group_required("User manager")}),
    path('um/set_groups/', views.set_groups, name='set_groups',
         kwargs={"check": group_required("User manager")})
]
