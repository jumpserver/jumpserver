# coding: utf-8
#

from django.utils.translation import ugettext as _

from django.views.generic import (
    TemplateView, CreateView, UpdateView, DetailView, ListView
)
from django.views.generic.edit import SingleObjectMixin

from common.permissions import PermissionsMixin, IsOrgAdmin

from .. import models, forms


__all__ = [
    'DatabaseAppPermissionListView', 'DatabaseAppPermissionCreateView',
    'DatabaseAppPermissionUpdateView', 'DatabaseAppPermissionDetailView',
    # 'DatabaseAppPermissionDatabaseAppView', 'DatabaseAppPermissionUserView'
]


class DatabaseAppPermissionListView(PermissionsMixin, TemplateView):
    template_name = 'perms/database_app_permission_list.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('DatabaseApp permission list')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DatabaseAppPermissionCreateView(PermissionsMixin, CreateView):
    template_name = 'perms/database_app_permission_create_update.html'
    model = models.DatabaseAppPermission
    form_class = forms.DatabaseAppPermissionCreateUpdateForm
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create DatabaseApp permission'),
            'api_action': 'create',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DatabaseAppPermissionUpdateView(PermissionsMixin, UpdateView):
    template_name = 'perms/database_app_permission_create_update.html'
    model = models.DatabaseAppPermission
    form_class = forms.DatabaseAppPermissionCreateUpdateForm
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Update DatabaseApp permission'),
            'api_action': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DatabaseAppPermissionDetailView(PermissionsMixin, DetailView):
    template_name = 'perms/database_app_permission_detail.html'
    model = models.DatabaseAppPermission
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('DatabaseApp permission detail')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


# class DatabaseAppPermissionUserView(PermissionsMixin,
#                                     SingleObjectMixin,
#                                     ListView):
#     pass
#
#
# class DatabaseAppPermissionDatabaseAppView(PermissionsMixin,
#                                            SingleObjectMixin,
#                                            ListView):
#     pass
