# coding: utf-8
#

from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.utils.translation import ugettext as _

from common.permissions import PermissionsMixin, IsSuperUser
from terminal.models import CommandStorage
from .. import forms


__all__ = [
    'CommandStorageListView', 'CommandStorageCreateView',
    'CommandStorageUpdateView'
]


class CommandStorageListView(PermissionsMixin, TemplateView):
    template_name = 'terminal/command_storage_list.html'
    permission_classes = [IsSuperUser]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Command storage list'),
            'is_command': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandStorageCreateView(PermissionsMixin, CreateView):
    template_name = 'terminal/command_storage_create_update.html'
    model = CommandStorage
    form_class = forms.CommandStorageCreateUpdateForm
    permission_classes = [IsSuperUser]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Create command storage'),
            'api_action': 'create'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandStorageUpdateView(PermissionsMixin, UpdateView):
    template_name = 'terminal/command_storage_create_update.html'
    model = CommandStorage
    form_class = forms.CommandStorageCreateUpdateForm
    permission_classes = [IsSuperUser]

    def get_initial(self):
        initial_data = {}
        for k, v in self.object.meta.items():
            _k = "{}_{}".format(self.object.type, k.lower())
            if k == 'HOSTS':
                v = ','.join(v)
            initial_data[_k] = v
        return initial_data

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Create command storage'),
            'api_action': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
