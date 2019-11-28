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
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class ReplayStorageCreateView(PermissionsMixin, CreateView):
    template_name = 'terminal/replay_storage_create_update.html'
    model = ReplayStorage
    form_class = forms.ReplayStorageCreateUpdateForm
    permission_classes = [IsSuperUser]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Create replay storage'),
            'api_action': 'create'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class ReplayStorageUpdateView(PermissionsMixin, UpdateView):
    template_name = 'terminal/replay_storage_create_update.html'
    model = ReplayStorage
    form_class = forms.ReplayStorageCreateUpdateForm
    permission_classes = [IsSuperUser]

    def get_initial(self):
        initial_data = {}
        for k, v in self.object.meta.items():
            _k = "{}_{}".format(self.object.type, k.lower())
            initial_data[_k] = v
        return initial_data

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Create replay storage'),
            'api_action': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
