# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals, absolute_import
import functools

from django.utils.translation import ugettext as _
from django.conf import settings
from django.db.models import Q
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin

from common.utils import search_object_attr
from .hands import AdminUserRequiredMixin, User, UserGroup, SystemUser, Asset, AssetGroup
from .models import AssetPermission
from .forms import AssetPermissionForm


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
        # Todo: Default order by lose asset connection num
        self.queryset = super(AssetPermissionListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.sort = sort = self.request.GET.get('sort', '-date_created')

        if keyword:
            self.queryset = self.queryset.filter(Q(users__name__contains=keyword) |
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


class AssetPermissionCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy('perms:asset-permission-list')
    success_message = _('Create asset permission <a href="%s"> %s </a> successfully.')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create asset permission'),
        }
        kwargs.update(context)
        return super(AssetPermissionCreateView, self).get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        return self.success_message % (
            reverse_lazy('perms:asset-permission-detail', kwargs={'pk': self.object.pk}),
            self.object.name,
        )


class AssetPermissionUpdateView(AdminUserRequiredMixin, UpdateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_message = _('Update asset permission <a href="%s"> %s </a> successfully.')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Update asset permission')
        }
        kwargs.update(context)
        return super(AssetPermissionUpdateView, self).get_context_data(**kwargs)

    def get_success_url(self):
        success_url = reverse_lazy('perms:asset-permission-detail', kwargs={'pk': self.object.pk})
        return success_url


class AssetPermissionDetailView(AdminUserRequiredMixin, DetailView):
    template_name = 'perms/asset_permission_detail.html'
    context_object_name = 'asset_permission'
    model = AssetPermission

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Asset permission detail'),
            'system_users_remain': [system_user for system_user in SystemUser.objects.all()
                                    if system_user not in self.object.system_users.all()],
            'system_users': self.object.system_users.all(),
        }
        kwargs.update(context)
        return super(AssetPermissionDetailView, self).get_context_data(**kwargs)


class AssetPermissionDeleteView(AdminUserRequiredMixin, DeleteView):
    model = AssetPermission
    template_name = 'perms/delete_confirm.html'
    success_url = reverse_lazy('perms:asset-permission-list')


class AssetPermissionUserListView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    template_name = 'perms/asset_permission_user_list.html'
    context_object_name = 'asset_permission'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetPermission.objects.all())
        self.keyword = self.request.GET.get('keyword', '')
        return super(AssetPermissionUserListView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.object.get_granted_users()
        if self.keyword:
            search_func = functools.partial(search_object_attr, value=self.keyword,
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
            'users_remain': [user for user in User.objects.all() if user not in users_granted],
            'user_groups': self.object.user_groups.all(),
            'user_groups_remain': [user_group for user_group in UserGroup.objects.all()
                                   if user_group not in user_groups_granted],
            'keyword': self.keyword,
        }
        kwargs.update(context)
        return super(AssetPermissionUserListView, self).get_context_data(**kwargs)


class AssetPermissionAssetListView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    template_name = 'perms/asset_permission_asset_list.html'
    context_object_name = 'asset_permission'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetPermission.objects.all())
        self.keyword = self.request.GET.get('keyword', '')
        return super(AssetPermissionAssetListView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.object.get_granted_assets()
        if self.keyword:
            search_func = functools.partial(search_object_attr, value=self.keyword,
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
            'assets_remain': (asset for asset in Asset.objects.all() if asset not in assets_granted),
            'asset_groups': self.object.asset_groups.all(),
            'asset_groups_remain': [asset_group for asset_group in AssetGroup.objects.all()
                                    if asset_group not in asset_groups_granted],
            'keyword': self.keyword,
        }
        kwargs.update(context)
        return super(AssetPermissionAssetListView, self).get_context_data(**kwargs)
