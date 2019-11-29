# coding: utf-8
#

from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.utils.translation import ugettext as _

from common.permissions import PermissionsMixin, IsSuperUser
from terminal.models import ReplayStorage
from .. import forms


__all__ = [
    'ReplayStorageListView', 'ReplayStorageCreateView',
    'ReplayStorageUpdateView'
]


class ReplayStorageListView(PermissionsMixin, TemplateView):
    template_name = 'terminal/replay_storage_list.html'
    permission_classes = [IsSuperUser]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Replay storage list'),
            'is_replay': True,
            'types': ['Server', 'S3', 'OSS', 'Azure']
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class ReplayStorageCreateUpdateViewMixin:
    model = ReplayStorage
    permission_classes = [IsSuperUser]
    default_storage_type = 'server'
    form_class = forms.ReplayStorageServerForm
    form_class_dict = {
        's3': forms.ReplayStorageS3Form,
        'oss': forms.ReplayStorageOSSForm,
        'azure': forms.ReplayStorageAzureForm
    }

    def get_storage_type(self):
        return self.default_storage_type

    def get_form_class(self):
        tp = self.get_storage_type()
        form_class = self.form_class_dict.get(tp)
        if form_class:
            return form_class
        return super().get_form_class()

    def get_initial(self):
        return {'type': self.get_storage_type()}


class ReplayStorageCreateView(ReplayStorageCreateUpdateViewMixin,
                              PermissionsMixin, CreateView):
    template_name = 'terminal/replay_storage_create_update.html'

    def get_storage_type(self):
        tp = self.request.GET.get("type", 'server').lower()
        return tp

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Create replay storage'),
            'api_action': 'create'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class ReplayStorageUpdateView(ReplayStorageCreateUpdateViewMixin,
                              PermissionsMixin, UpdateView):
    template_name = 'terminal/replay_storage_create_update.html'

    def get_storage_type(self):
        return self.object.type

    def get_initial(self):
        initial_data = super().get_initial()
        for k, v in self.object.meta.items():
            _k = "{}_{}".format(self.object.type, k.lower())
            initial_data[_k] = v
        return initial_data

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Update replay storage'),
            'api_action': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
