# coding: utf-8
#

from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.utils.translation import ugettext as _

from common.permissions import PermissionsMixin, IsSuperUser
from terminal.models import CommandStorage
from .. import forms, const


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
            'type_choices': const.COMMAND_STORAGE_TYPE_CHOICES,
            'is_command': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandStorageCreateUpdateViewMixin:
    model = CommandStorage
    permission_classes = [IsSuperUser]
    default_storage_type = const.COMMAND_STORAGE_TYPE_SERVER
    form_class = forms.CommandStorageServerForm
    form_class_dict = {
        const.COMMAND_STORAGE_TYPE_ES: forms.CommandStorageTypeESForm
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


class CommandStorageCreateView(CommandStorageCreateUpdateViewMixin,
                               PermissionsMixin, CreateView):
    template_name = 'terminal/command_storage_create_update.html'

    def get_storage_type(self):
        tp = self.request.GET.get("type", self.default_storage_type).lower()
        return tp

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Create command storage'),
            'api_action': 'create'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandStorageUpdateView(CommandStorageCreateUpdateViewMixin,
                               PermissionsMixin, UpdateView):
    template_name = 'terminal/command_storage_create_update.html'

    def get_storage_type(self):
        return self.object.type

    def get_initial(self):
        initial_data = super().get_initial()
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
