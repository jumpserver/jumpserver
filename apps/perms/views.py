# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals, absolute_import

from django.utils.translation import ugettext as _
from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from django.conf import settings
from django.db.models import Q

from .hands import AdminUserRequiredMixin, Node, User, UserGroup, Asset, SystemUser
from .models import AssetPermission, NodePermission
from .forms import AssetPermissionForm


class AssetPermissionListView(AdminUserRequiredMixin, ListView):
    model = AssetPermission
    template_name = 'perms/asset_permission_list.html'
    paginate_by = settings.DISPLAY_PER_PAGE
    user = user_group = asset = node = system_user = q = ""

    def get_queryset(self):
        self.q = self.request.GET.get('q', '')
        self.user = self.request.GET.get("user", '')
        self.user_group = self.request.GET.get("user_group", '')
        self.asset = self.request.GET.get('asset', '')
        self.node = self.request.GET.get('node', '')
        self.system_user = self.request.GET.get('system_user', '')
        filter_kwargs = dict()
        if self.user:
            filter_kwargs['users__name'] = self.user
        if self.user_group:
            filter_kwargs['user_groups__name'] = self.user_group
        if self.asset:
            filter_kwargs['assets__hostname'] = self.asset
        if self.node:
            filter_kwargs['nodes__value'] = self.node
        if self.system_user:
            filter_kwargs['system_users__name'] = self.system_user
        queryset = self.model.objects.filter(**filter_kwargs)
        if self.q:
            queryset = queryset.filter(
                Q(name__contains=self.q) |
                Q(users__name=self.q) |
                Q(user_groups__name=self.q) |
                Q(assets__hostname=self.q) |
                Q(nodes__value=self.q) |
                Q(system_users__name=self.q)
            )
        queryset = queryset.order_by('-date_start')
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'user_list': User.objects.all().values_list('name', flat=True),
            'user_group_list': UserGroup.objects.all().values_list('name', flat=True),
            'asset_list': Asset.objects.all().values_list('hostname', flat=True),
            'node_list': Node.objects.all().values_list('value', flat=True),
            'system_user_list': SystemUser.objects.all().values_list('name', flat=True),
            'user': self.user,
            'user_group': self.user_group,
            'asset': self.asset,
            'node': self.node,
            'system_user': self.system_user,
            'q': self.q,
            'action': _('Asset permission list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionCreateView(AdminUserRequiredMixin, CreateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy('perms:asset-permission-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create asset permission'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionUpdateView(AdminUserRequiredMixin, UpdateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy("perms:asset-permission-list")

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Update asset permission')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionDeleteView(AdminUserRequiredMixin, DeleteView):
    model = AssetPermission
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('perms:asset-permission-list')


