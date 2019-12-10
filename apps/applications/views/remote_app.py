#  coding: utf-8
#

from django.http import Http404
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView

from common.permissions import PermissionsMixin, IsOrgAdmin, IsValidUser

from ..models import RemoteApp
from .. import forms, const


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
            'type_choices': const.REMOTE_APP_TYPE_CHOICES,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class BaseRemoteAppCreateUpdateView:
    template_name = 'applications/remote_app_create_update.html'
    model = RemoteApp
    permission_classes = [IsOrgAdmin]
    default_type = const.REMOTE_APP_TYPE_CHROME
    form_class = forms.RemoteAppChromeForm
    form_class_choices = {
        const.REMOTE_APP_TYPE_CHROME: forms.RemoteAppChromeForm,
        const.REMOTE_APP_TYPE_MYSQL_WORKBENCH: forms.RemoteAppMySQLWorkbenchForm,
        const.REMOTE_APP_TYPE_VMWARE_CLIENT: forms.RemoteAppVMwareForm,
        const.REMOTE_APP_TYPE_CUSTOM: forms.RemoteAppCustomForm
    }

    def get_initial(self):
        return {'type': self.get_type()}

    def get_type(self):
        return self.default_type

    def get_form_class(self):
        tp = self.get_type()
        form_class = self.form_class_choices.get(tp)
        if not form_class:
            raise Http404()
        return form_class


class RemoteAppCreateView(BaseRemoteAppCreateUpdateView,
                          PermissionsMixin, CreateView):

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Applications'),
            'action': _('Create RemoteApp'),
            'api_action': 'create'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_type(self):
        tp = self.request.GET.get("type")
        if tp:
            return tp.lower()
        return super().get_type()


class RemoteAppUpdateView(BaseRemoteAppCreateUpdateView,
                          PermissionsMixin, UpdateView):

    def get_initial(self):
        initial_data = super().get_initial()
        params = {k: v for k, v in self.object.params.items()}
        initial_data.update(params)
        return initial_data

    def get_type(self):
        return self.object.type

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Applications'),
            'action': _('Update RemoteApp'),
            'api_action': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


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
