# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals


from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import (
    CreateView, UpdateView
)
from django.views.generic.detail import DetailView

from common.const import (
    create_success_msg, update_success_msg, KEY_CACHE_RESOURCES_ID
)
from common.utils import get_logger
from common.permissions import (
    PermissionsMixin, IsOrgAdmin,
    CanUpdateDeleteUser,
)
from orgs.utils import current_org
from .. import forms
from ..models import User, UserGroup
from ..utils import get_password_check_rules, is_need_unblock
from ..signals import post_user_create

__all__ = [
    'UserListView', 'UserCreateView', 'UserDetailView',
    'UserUpdateView', 'UserGrantedAssetView',
    'UserBulkUpdateView', 'UserAssetPermissionListView',
]

logger = get_logger(__name__)


class UserListView(PermissionsMixin, TemplateView):
    template_name = 'users/user_list.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _('Users'),
            'action': _('User list'),
        })
        return context


class UserCreateView(PermissionsMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = forms.UserCreateForm
    template_name = 'users/user_create.html'
    success_url = reverse_lazy('users:user-list')
    success_message = create_success_msg
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        check_rules = get_password_check_rules()
        context = {
            'app': _('Users'),
            'action': _('Create user'),
            'password_check_rules': check_rules,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save(commit=False)
        user.created_by = self.request.user.username or 'System'
        user.save()
        if current_org and current_org.is_real():
            user.related_user_orgs.add(current_org.id)
        post_user_create.send(self.__class__, user=user)
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super(UserCreateView, self).get_form_kwargs()
        data = {'request': self.request}
        kwargs.update(data)
        return kwargs


class UserUpdateView(PermissionsMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = forms.UserUpdateForm
    template_name = 'users/user_update.html'
    context_object_name = 'user_object'
    success_url = reverse_lazy('users:user-list')
    success_message = update_success_msg
    permission_classes = [IsOrgAdmin]

    def _deny_permission(self):
        obj = self.get_object()
        return not self.request.user.is_superuser and obj.is_superuser

    def get(self, request, *args, **kwargs):
        if self._deny_permission():
            return redirect(self.success_url)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        check_rules = get_password_check_rules()
        context = {
            'app': _('Users'),
            'action': _('Update user'),
            'password_check_rules': check_rules,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self):
        kwargs = super(UserUpdateView, self).get_form_kwargs()
        data = {'request': self.request}
        kwargs.update(data)
        return kwargs


class UserBulkUpdateView(PermissionsMixin, TemplateView):
    model = User
    form_class = forms.UserBulkUpdateForm
    template_name = 'users/user_bulk_update.html'
    success_url = reverse_lazy('users:user-list')
    success_message = _("Bulk update user success")
    form = None
    id_list = None
    permission_classes = [IsOrgAdmin]

    def get(self, request, *args, **kwargs):
        spm = request.GET.get('spm', '')
        users_id = cache.get(KEY_CACHE_RESOURCES_ID.format(spm))
        if kwargs.get('form'):
            self.form = kwargs['form']
        elif users_id:
            self.form = self.form_class(initial={'users': users_id})
        else:
            self.form = self.form_class()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, self.success_message)
            return redirect(self.success_url)
        else:
            return self.get(request, form=form, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': _('Bulk update user'),
            'form': self.form,
            'users_selected': self.id_list,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserDetailView(PermissionsMixin, DetailView):
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = "user_object"
    key_prefix_block = "_LOGIN_BLOCK_{}"
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        user = self.get_object()
        key_block = self.key_prefix_block.format(user.username)
        groups = UserGroup.objects.exclude(id__in=self.object.groups.all())
        context = {
            'app': _('Users'),
            'action': _('User detail'),
            'groups': groups,
            'unblock': is_need_unblock(key_block),
            'can_update': CanUpdateDeleteUser.has_update_object_permission(
                self.request, self, user
            ),
            'can_delete': CanUpdateDeleteUser.has_delete_object_permission(
                self.request, self, user
            ),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        org_users = current_org.get_org_members().values_list('id', flat=True)
        queryset = queryset.filter(id__in=org_users)
        return queryset


class UserGrantedAssetView(PermissionsMixin, DetailView):
    model = User
    template_name = 'users/user_granted_asset.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('User granted assets'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserAssetPermissionListView(PermissionsMixin, DetailView):
    model = User
    template_name = 'users/user_asset_permission.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('Asset permission'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
