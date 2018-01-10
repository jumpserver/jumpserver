# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals, absolute_import

from django.utils.translation import ugettext as _
from django.conf import settings
from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic.edit import DeleteView, FormView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.contrib import messages

from common.const import create_success_msg, update_success_msg
from .hands import AdminUserRequiredMixin, User, UserGroup, SystemUser, \
    Asset, AssetGroup
from .models import AssetPermission
from .forms import AssetPermissionForm


class AssetPermissionListView(AdminUserRequiredMixin, ListView):
    model = AssetPermission
    context_object_name = 'asset_permission_list'
    template_name = 'perms/asset_permission_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Asset permission list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy('perms:asset-permission-list')
    success_message = create_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create asset permission'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy("perms:asset-permission-list")
    success_message = update_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Update asset permission')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionDetailView(AdminUserRequiredMixin, DetailView):
    template_name = 'perms/asset_permission_detail.html'
    context_object_name = 'asset_permission'
    model = AssetPermission

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Asset permission detail'),
            'system_users_remain': [
                system_user for system_user in SystemUser.objects.all()
                if system_user not in self.object.system_users.all()],
            'system_users': self.object.system_users.all(),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionDeleteView(AdminUserRequiredMixin, DeleteView):
    model = AssetPermission
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('perms:asset-permission-list')


class AssetPermissionUserView(AdminUserRequiredMixin,
                              SingleObjectMixin,
                              ListView):
    template_name = 'perms/asset_permission_user.html'
    context_object_name = 'asset_permission'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetPermission.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.object.get_granted_users()
        return queryset

    def get_context_data(self, **kwargs):
        users_granted = self.get_queryset()
        groups_granted = self.object.user_groups.all()
        context = {
            'app': _('Perms'),
            'action': _('Asset permission user list'),
            'users_remain': User.objects.exclude(id__in=[user.id for user in users_granted]),
            'user_groups': self.object.user_groups.all(),
            'user_groups_remain': UserGroup.objects.exclude(id__in=[group.id for group in groups_granted])
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionAssetView(AdminUserRequiredMixin,
                               SingleObjectMixin,
                               ListView):
    template_name = 'perms/asset_permission_asset.html'
    context_object_name = 'asset_permission'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetPermission.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.object.get_granted_assets()
        return queryset

    def get_context_data(self, **kwargs):
        assets_granted = self.get_queryset()
        groups_granted = self.object.asset_groups.all()
        context = {
            'app': _('Perms'),
            'action': _('Asset permission asset list'),
            'assets_remain': Asset.objects.exclude(id__in=[asset.id for asset in assets_granted]),
            'asset_groups': self.object.asset_groups.all(),
            'asset_groups_remain': AssetGroup.objects.exclude(id__in=[group.id for group in groups_granted])
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
