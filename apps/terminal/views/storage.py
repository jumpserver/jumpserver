# coding: utf-8
#

from django.http import Http404
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.utils.translation import ugettext as _

from common.permissions import PermissionsMixin, IsSuperUser
from terminal.models import ReplayStorage, CommandStorage
from .. import forms, const


__all__ = [
    'ReplayStorageListView', 'ReplayStorageCreateView',
    'ReplayStorageUpdateView', 'CommandStorageListView',
    'CommandStorageCreateView', 'CommandStorageUpdateView'
]


class ReplayStorageListView(PermissionsMixin, TemplateView):
    template_name = 'terminal/replay_storage_list.html'
    permission_classes = [IsSuperUser]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Replay storage list'),
            'is_replay': True,
            'type_choices': const.REPLAY_STORAGE_TYPE_CHOICES_EXTENDS,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandStorageListView(PermissionsMixin, TemplateView):
    template_name = 'terminal/command_storage_list.html'
    permission_classes = [IsSuperUser]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Command storage list'),
            'type_choices': const.COMMAND_STORAGE_TYPE_CHOICES_EXTENDS,
            'is_command': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class BaseStorageCreateUpdateViewMixin:
    permission_classes = [IsSuperUser]
    default_type = None
    form_class = None
    form_class_choices = {}

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


class ReplayStorageCreateUpdateViewMixin(BaseStorageCreateUpdateViewMixin):
    model = ReplayStorage
    default_type = const.REPLAY_STORAGE_TYPE_S3
    form_class = forms.ReplayStorageS3Form
    form_class_choices = {
        const.REPLAY_STORAGE_TYPE_S3: forms.ReplayStorageS3Form,
        const.REPLAY_STORAGE_TYPE_CEPH: forms.ReplayStorageCephForm,
        const.REPLAY_STORAGE_TYPE_SWIFT: forms.ReplayStorageSwiftForm,
        const.REPLAY_STORAGE_TYPE_OSS: forms.ReplayStorageOSSForm,
        const.REPLAY_STORAGE_TYPE_AZURE: forms.ReplayStorageAzureForm
    }


class ReplayStorageCreateView(ReplayStorageCreateUpdateViewMixin,
                              PermissionsMixin, CreateView):
    template_name = 'terminal/replay_storage_create_update.html'

    def get_type(self):
        tp = self.request.GET.get("type")
        if tp:
            return tp.lower()
        return super().get_type()

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

    def get_initial(self):
        initial_data = super().get_initial()
        for k, v in self.object.meta.items():
            _k = "{}_{}".format(self.object.type, k.lower())
            initial_data[_k] = v
        return initial_data

    def get_type(self):
        return self.object.type

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Update replay storage'),
            'api_action': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandStorageCreateUpdateViewMixin(BaseStorageCreateUpdateViewMixin):
    model = CommandStorage
    default_type = const.COMMAND_STORAGE_TYPE_ES
    form_class = forms.CommandStorageTypeESForm
    form_class_choices = {
        const.COMMAND_STORAGE_TYPE_ES: forms.CommandStorageTypeESForm
    }


class CommandStorageCreateView(CommandStorageCreateUpdateViewMixin,
                               PermissionsMixin, CreateView):
    template_name = 'terminal/command_storage_create_update.html'

    def get_type(self):
        tp = self.request.GET.get("type")
        if tp:
            return tp.lower()
        return super().get_type()

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

    def get_initial(self):
        initial_data = super().get_initial()
        for k, v in self.object.meta.items():
            _k = "{}_{}".format(self.object.type, k.lower())
            if k == 'HOSTS':
                v = ','.join(v)
            initial_data[_k] = v
        return initial_data

    def get_type(self):
        return self.object.type

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Update command storage'),
            'api_action': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

