#  coding: utf-8
#

from django.utils.translation import ugettext as _
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy


from common.permissions import PermissionsMixin, IsOrgAdmin, IsValidUser
from common.const import create_success_msg, update_success_msg

from ..models import RemoteApp
from .. import forms


__all__ = [
    'RemoteAppListView', 'RemoteAppCreateView', 'RemoteAppUpdateView',
    'RemoteAppDetailView', 'UserRemoteAppListView',
]


class RemoteAppListView(PermissionsMixin, TemplateView):
    template_name = 'applications/remote_app_list.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Applications'),
            'action': _('RemoteApp list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class RemoteAppCreateView(PermissionsMixin, SuccessMessageMixin, CreateView):
    template_name = 'applications/remote_app_create_update.html'
    model = RemoteApp
    form_class = forms.RemoteAppCreateUpdateForm
    success_url = reverse_lazy('applications:remote-app-list')
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Applications'),
            'action': _('Create RemoteApp'),
            'type': 'create'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        return create_success_msg % ({'name': cleaned_data['name']})


class RemoteAppUpdateView(PermissionsMixin, SuccessMessageMixin, UpdateView):
    template_name = 'applications/remote_app_create_update.html'
    model = RemoteApp
    form_class = forms.RemoteAppCreateUpdateForm
    success_url = reverse_lazy('applications:remote-app-list')
    permission_classes = [IsOrgAdmin]

    def get_initial(self):
        return {k: v for k, v in self.object.params.items()}

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Applications'),
            'action': _('Update RemoteApp'),
            'type': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        return update_success_msg % ({'name': cleaned_data['name']})


class RemoteAppDetailView(PermissionsMixin, DetailView):
    template_name = 'applications/remote_app_detail.html'
    model = RemoteApp
    context_object_name = 'remote_app'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Applications'),
            'action': _('RemoteApp detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserRemoteAppListView(PermissionsMixin, TemplateView):
    template_name = 'applications/user_remote_app_list.html'
    permission_classes = [IsValidUser]

    def get_context_data(self, **kwargs):
        context = {
            'action': _('My RemoteApp'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
