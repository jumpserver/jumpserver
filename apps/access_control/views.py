from django.shortcuts import render

# Create your views here.
# coding: utf-8
#

from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from common.permissions import PermissionsMixin, IsOrgAdmin
from .forms import AccessControlForm


class AccessControlListView(PermissionsMixin, TemplateView):
    template_name = 'access_control/access_control_list.html'
    permission_classes = [IsOrgAdmin]


class AccessControlCreateView(PermissionsMixin, CreateView):
    template_name = 'access_control/access_control_create_update.html'
    form_class = AccessControlForm
    permission_classes = [IsOrgAdmin]

#
# class DatabaseAppUpdateView(BaseDatabaseAppCreateUpdateView, UpdateView):
#
#     def get_type(self):
#         return self.object.type
#
#     def get_context_data(self, **kwargs):
#         context = {
#             'app': _('Applications'),
#             'action': _('Create DatabaseApp'),
#             'api_action': 'update'
#         }
#         kwargs.update(context)
#         return super().get_context_data(**kwargs)
#
#
# class DatabaseAppDetailView(PermissionsMixin, DetailView):
#     template_name = 'applications/database_app_detail.html'
#     model = models.DatabaseApp
#     context_object_name = 'database_app'
#     permission_classes = [IsOrgAdmin]
#
#     def get_context_data(self, **kwargs):
#         context = {
#             'app': _('Applications'),
#             'action': _('DatabaseApp detail'),
#         }
#         kwargs.update(context)
#         return super().get_context_data(**kwargs)
