from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import ProtectedError
from django.forms import ModelForm
from django.http import HttpResponseBadRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django_jinja.views.generic import ListView, DeleteView, UpdateView, CreateView

from viva.jinja2 import get_groups_as_string
from viva.settings import DEFENDER_COOLOFF_TIME


class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']


class UserUpdateView(SuccessMessageMixin, UpdateView):
    form_class = UserForm
    model = User
    template_name = "accounts/profile.html"
    success_url = reverse_lazy('accounts:profile')
    success_message = "Your profile has been updated successfully."

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        form.instance.is_active = User.objects.get(username=self.request.user.username).is_active
        return super(UserUpdateView, self).form_valid(form)


class UserEditView(SuccessMessageMixin, UpdateView):
    form_class = UserForm
    model = User
    template_name = "accounts/edit_user.html"
    success_url = reverse_lazy('accounts:user_list')

    def get_context_data(self, **kwargs):
        kwargs['groups'] = Group.objects.order_by('name')
        return super(UserEditView, self).get_context_data(**kwargs)


class ChangeUserPasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = "accounts/change_password.html"
    success_url = reverse_lazy("accounts:change_password")
    success_message = "Your password has been updated successfully."


class UserCreateForm(UserCreationForm, UserForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'is_active']


class UserCreateView(SuccessMessageMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "accounts/create_user.html"
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        form.instance.is_active = True
        return super(UserCreateView, self).form_valid(form)


class UserApplyView(SuccessMessageMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "registration/apply_user.html"
    success_url = reverse_lazy('base:start')

    def form_valid(self, form):
        form.instance.is_active = False
        return super(UserApplyView, self).form_valid(form)


class UserListView(ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"


class UserDeleteView(DeleteView):
    model = User
    template_name = "accounts/delete_user.html"
    success_url = reverse_lazy('accounts:user_list')
    error_url = reverse_lazy('accounts:user_list')

    def get_error_url(self):
        if self.error_url:
            return self.error_url.format(**self.object.__dict__)
        else:
            raise ImproperlyConfigured("No error URL to redirect to. Provide a error_url.")

    def delete(self, request, *args, **kwargs):
        """
        Call the delete() method on the fetched object and then redirect.
        """
        self.object = self.get_object()
        try:
            self.object.delete()
            return HttpResponseRedirect(self.get_success_url())
        except ProtectedError:
            return HttpResponseRedirect(self.get_error_url())


def set_user_password(request):
    """If request method is 'POST' this method verifies if the entered passwords are equal and valid and if so
    eventually sets the user's new password.
    :parameter request: the request
    """
    if request.method == 'POST' and request.is_ajax() and \
            all(x in request.POST for x in ["username", "password1", "password2"]):
        try:
            user = User.objects.get(username=request.POST.get("username"))
            password = request.POST.get("password1")
            if password != request.POST.get("password2"):
                return HttpResponseBadRequest("Passwords do not match!")
            validate_password(password)
            user.set_password(password)
            user.save()
            return HttpResponse("Set password successfully!")
        except User.DoesNotExist:
            pass
        except ValidationError as e:
            return HttpResponseBadRequest("<br>".join(e.messages))
    return HttpResponseBadRequest("")


def set_groups(request):
    """If request method is 'POST' this method ...
    :parameter request: the request
    """
    if request.method == 'POST' and request.is_ajax() and all(x in request.POST for x in ["checked[]", "username"]):
        user = User.objects.get(username=request.POST.get("username"))
        for group in Group.objects.all():
            if str(group.id) in request.POST.getlist("checked[]"):
                group.user_set.add(user)
            else:
                group.user_set.remove(user)
        return HttpResponse(get_groups_as_string(user.groups.all()))
    return HttpResponseBadRequest()


def get_blocked_page(request: WSGIRequest):
    """Returns the rendered page for client that are blocked by defender

    :param request: the request
    :return: the rendered page
    """
    return render(request, "registration/login-blocked.html", {"DEFENDER_COOLOFF_TIME": DEFENDER_COOLOFF_TIME})
