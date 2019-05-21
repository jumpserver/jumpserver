# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals, absolute_import

from django.utils.translation import ugettext as _
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView
from django.views.generic.edit import DeleteView, SingleObjectMixin
from django.urls import reverse_lazy
from django.conf import settings

from common.permissions import AdminUserRequiredMixin
from orgs.utils import current_org
from perms.hands import Node, Asset, SystemUser, User, UserGroup
from perms.models import AssetPermission, Action
from perms.forms import AssetPermissionForm
from perms.const import PERMS_ACTION_NAME_ALL


__all__ = [
    'AssetPermissionListView', 'AssetPermissionCreateView',
    'AssetPermissionUpdateView', 'AssetPermissionDetailView',
    'AssetPermissionDeleteView', 'AssetPermissionUserView',
    'AssetPermissionAssetView',

]


class AssetPermissionListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'perms/asset_permission_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Asset permission list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionCreateView(AdminUserRequiredMixin, CreateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy('perms:asset-permission-list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        nodes_id = self.request.GET.get("nodes")
        assets_id = self.request.GET.get("assets")

        if nodes_id:
            nodes_id = nodes_id.split(",")
            nodes = Node.objects.filter(id__in=nodes_id).exclude(id=Node.root().id)
            form['nodes'].initial = nodes
        if assets_id:
            assets_id = assets_id.split(",")
            assets = Asset.objects.filter(id__in=assets_id)
            form['assets'].initial = assets
        form['actions'].initial = Action.objects.get(name=PERMS_ACTION_NAME_ALL)

        return form

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


class AssetPermissionDetailView(AdminUserRequiredMixin, DetailView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_detail.html'
    success_url = reverse_lazy("perms:asset-permission-list")

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Asset permission detail'),
            'system_users_remain': SystemUser.objects.exclude(
                granted_by_permissions=self.object
            ),
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
    paginate_by = settings.DISPLAY_PER_PAGE
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetPermission.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = list(self.object.get_all_users())
        return queryset

    def get_context_data(self, **kwargs):

        context = {
            'app': _('Perms'),
            'action': _('Asset permission user list'),
            'users_remain': current_org.get_org_users().exclude(
                assetpermission=self.object
            ),
            'user_groups_remain': UserGroup.objects.exclude(
                assetpermission=self.object
            )
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionAssetView(AdminUserRequiredMixin,
                               SingleObjectMixin,
                               ListView):
    template_name = 'perms/asset_permission_asset.html'
    context_object_name = 'asset_permission'
    paginate_by = settings.DISPLAY_PER_PAGE
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset = AssetPermission.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = list(self.object.get_all_assets())
        return queryset

    def get_context_data(self, **kwargs):
        assets_granted = self.get_queryset()
        context = {
            'app': _('Perms'),
            'action': _('Asset permission asset list'),
            'assets_remain': Asset.objects.exclude(id__in=[a.id for a in assets_granted]),
            'nodes_remain': Node.objects.exclude(granted_by_permissions=self.object),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)