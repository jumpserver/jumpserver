# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals, absolute_import

import functools

from django.utils.translation import ugettext as _
from django.db import transaction
from django.conf import settings
from django.db.models import Q
from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic.edit import DeleteView, FormView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin

from common.utils import search_object_attr
from .hands import AdminUserRequiredMixin, User, UserGroup, SystemUser, \
    Asset, AssetGroup
from .models import AssetPermission
from .forms import AssetPermissionForm
from .utils import associate_system_users_and_assets


class AssetPermissionListView(AdminUserRequiredMixin, ListView):
    model = AssetPermission
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'asset_permission_list'
    template_name = 'perms/asset_permission_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Asset permission list'),
            'keyword': self.keyword,
        }
        kwargs.update(context)
        return super(AssetPermissionListView, self).get_context_data(**kwargs)

    def get_queryset(self):
        self.queryset = super(AssetPermissionListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.sort = sort = self.request.GET.get('sort', '-date_created')

        if keyword:
            self.queryset = self.queryset\
                .filter(Q(users__name__contains=keyword) |
                        Q(users__username__contains=keyword) |
                        Q(user_groups__name__contains=keyword) |
                        Q(assets__ip__contains=keyword) |
                        Q(assets__hostname__contains=keyword) |
                        Q(system_users__username__icontains=keyword) |
                        Q(system_users__name__icontains=keyword) |
                        Q(asset_groups__name__icontains=keyword) |
                        Q(comment__icontains=keyword) |
                        Q(name__icontains=keyword)).distinct()
        if sort:
            self.queryset = self.queryset.order_by(sort)
        return self.queryset


class AssetPermissionCreateView(AdminUserRequiredMixin,
                                SuccessMessageMixin,
                                CreateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy('perms:asset-permission-list')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        return super(AssetPermissionCreateView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create asset permission'),
        }
        kwargs.update(context)
        return super(AssetPermissionCreateView, self).get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        url = reverse_lazy('perms:asset-permission-detail',
                           kwargs={'pk': self.object.pk})
        success_message = _(
            'Create asset permission <a href="{url}"> {name} </a> '
            'successfully.'.format(url=url, name=self.object.name))
        return success_message

    def form_valid(self, form):
        assets = form.cleaned_data['assets']
        asset_groups = form.cleaned_data['asset_groups']
        system_users = form.cleaned_data['system_users']
        associate_system_users_and_assets(system_users, assets, asset_groups)
        response = super(AssetPermissionCreateView, self).form_valid(form)
        self.object.created_by = self.request.user.name
        self.object.save()
        return response


class AssetPermissionUpdateView(AdminUserRequiredMixin, UpdateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_message = _(
        'Update asset permission <a href="{url}"> {name} </a> successfully.'
    )
    success_url = reverse_lazy("perms:asset-permission-list")

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Update asset permission')
        }
        kwargs.update(context)
        return super(AssetPermissionUpdateView, self).get_context_data(**kwargs)

    def get_success_message(self):
        url = reverse_lazy('perms:asset-permission-detail',
                           kwargs={'pk': self.object.pk})
        return self.success_message.format(
            url=url, name=self.object.name
        )

    def form_valid(self, form):
        assets = form.cleaned_data['assets']
        asset_groups = form.cleaned_data['asset_groups']
        system_users = form.cleaned_data['system_users']
        associate_system_users_and_assets(system_users, assets, asset_groups)
        return super(AssetPermissionUpdateView, self).form_valid(form)


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
        return super(AssetPermissionDetailView, self).get_context_data(**kwargs)


class AssetPermissionDeleteView(AdminUserRequiredMixin, DeleteView):
    model = AssetPermission
    template_name = 'perms/delete_confirm.html'
    success_url = reverse_lazy('perms:asset-permission-list')


class AssetPermissionUserView(AdminUserRequiredMixin,
                              SingleObjectMixin,
                              ListView):
    template_name = 'perms/asset_permission_user.html'
    context_object_name = 'asset_permission'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetPermission.objects.all())
        self.keyword = self.request.GET.get('keyword', '')
        return super(AssetPermissionUserView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.object.get_granted_users()
        if self.keyword:
            search_func = functools.partial(
                search_object_attr,
                value=self.keyword,
                attr_list=['username', 'name', 'email'],
                ignore_case=True)
            queryset = filter(search_func, queryset)
        return queryset

    def get_context_data(self, **kwargs):
        users_granted = self.get_queryset()
        user_groups_granted = self.object.user_groups.all()
        context = {
            'app': _('Perms'),
            'action': _('Asset permission user list'),
            'users_remain': [
                user for user in User.objects.all()
                if user not in users_granted],
            'user_groups': self.object.user_groups.all(),
            'user_groups_remain': [
                user_group for user_group in UserGroup.objects.all()
                if user_group not in user_groups_granted],
            'keyword': self.keyword,
        }
        kwargs.update(context)
        return super(AssetPermissionUserView, self).get_context_data(**kwargs)


class AssetPermissionAssetView(AdminUserRequiredMixin,
                               SingleObjectMixin,
                               ListView):
    template_name = 'perms/asset_permission_asset.html'
    context_object_name = 'asset_permission'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetPermission.objects.all())
        self.keyword = self.request.GET.get('keyword', '')
        return super(AssetPermissionAssetView, self)\
            .get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.object.get_granted_assets()
        if self.keyword:
            search_func = functools.partial(
                search_object_attr, value=self.keyword,
                attr_list=['hostname', 'ip'],
                ignore_case=True)
            queryset = filter(search_func, queryset)
        return queryset

    def get_context_data(self, **kwargs):
        assets_granted = self.get_queryset()
        asset_groups_granted = self.object.user_groups.all()
        context = {
            'app': _('Perms'),
            'action': _('Asset permission asset list'),
            'assets_remain': [
                asset for asset in Asset.objects.all()
                if asset not in assets_granted],
            'asset_groups': self.object.asset_groups.all(),
            'asset_groups_remain': [
                asset_group for asset_group in AssetGroup.objects.all()
                if asset_group not in asset_groups_granted],
            'keyword': self.keyword,
        }
        kwargs.update(context)
        return super(AssetPermissionAssetView, self).get_context_data(**kwargs)
