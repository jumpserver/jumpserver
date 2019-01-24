# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from django.utils.translation import ugettext as _
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView
from django.contrib.messages.views import SuccessMessageMixin

from common.utils import get_logger
from common.const import create_success_msg, update_success_msg
from common.permissions import AdminUserRequiredMixin
from orgs.utils import current_org
from ..models import User, UserGroup
from .. import forms

__all__ = ['UserGroupListView', 'UserGroupCreateView', 'UserGroupDetailView',
           'UserGroupUpdateView', 'UserGroupGrantedAssetView']
logger = get_logger(__name__)


class UserGroupListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'users/user_group_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('User group list')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserGroupCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = UserGroup
    form_class = forms.UserGroupForm
    template_name = 'users/user_group_create_update.html'
    success_url = reverse_lazy('users:user-group-list')
    success_message = create_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('Create user group'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserGroupUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = UserGroup
    form_class = forms.UserGroupForm
    template_name = 'users/user_group_create_update.html'
    success_url = reverse_lazy('users:user-group-list')
    success_message = update_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('Update user group'),

        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserGroupDetailView(AdminUserRequiredMixin, DetailView):
    model = UserGroup
    context_object_name = 'user_group'
    template_name = 'users/user_group_detail.html'

    def get_context_data(self, **kwargs):
        users = current_org.get_org_users().exclude(id__in=self.object.users.all())
        context = {
            'app': _('Users'),
            'action': _('User group detail'),
            'users': users,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserGroupGrantedAssetView(AdminUserRequiredMixin, DetailView):
    model = UserGroup
    template_name = 'users/user_group_granted_asset.html'
    context_object_name = 'user_group'
    object = None

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('User group granted asset'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
