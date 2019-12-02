# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals, absolute_import

from django.utils.translation import ugettext as _
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView
from django.views.generic.edit import DeleteView, SingleObjectMixin
from django.urls import reverse_lazy
from django.conf import settings

from common.permissions import PermissionsMixin, IsOrgAdmin
from orgs.utils import current_org
from perms.hands import Node, Asset, SystemUser, UserGroup
from perms.models import AssetPermission
from perms.forms import AssetPermissionForm


__all__ = [
    'AssetPermissionListView', 'AssetPermissionCreateView',
    'AssetPermissionUpdateView', 'AssetPermissionDetailView',
    'AssetPermissionDeleteView', 'AssetPermissionUserView',
    'AssetPermissionAssetView',

]


class AssetPermissionListView(PermissionsMixin, TemplateView):
    template_name = 'perms/asset_permission_list.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Asset permission list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionCreateView(PermissionsMixin, CreateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy('perms:asset-permission-list')
    permission_classes = [IsOrgAdmin]

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        nodes_id = self.request.GET.get("nodes")
        assets_id = self.request.GET.get("assets")

        if nodes_id:
            nodes_id = nodes_id.split(",")
            nodes = Node.objects.filter(id__in=nodes_id)\
                .exclude(id=Node.org_root().id)
            form.set_nodes_initial(nodes)
        if assets_id:
            assets_id = assets_id.split(",")
            assets = Asset.objects.filter(id__in=assets_id)
            form.set_assets_initial(assets)
        return form

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create asset permission'),
            'api_action': "create",
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionUpdateView(PermissionsMixin, UpdateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy("perms:asset-permission-list")
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Update asset permission'),
            'api_action': "update",
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionDetailView(PermissionsMixin, DetailView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_detail.html'
    success_url = reverse_lazy("perms:asset-permission-list")
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Asset permission detail'),

        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionDeleteView(PermissionsMixin, DeleteView):
    model = AssetPermission
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('perms:asset-permission-list')
    permission_classes = [IsOrgAdmin]


class AssetPermissionUserView(PermissionsMixin,
                              SingleObjectMixin,
                              ListView):
    template_name = 'perms/asset_permission_user.html'
    context_object_name = 'asset_permission'
    paginate_by = settings.DISPLAY_PER_PAGE
    object = None
    permission_classes = [IsOrgAdmin]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetPermission.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = list(self.object.get_all_users())
        return queryset

    def get_context_data(self, **kwargs):
        users = [str(i) for i in self.object.users.all().values_list('id', flat=True)]
        user_groups_remain = UserGroup.objects.exclude(
            assetpermission=self.object)
        context = {
            'app': _('Perms'),
            'action': _('Asset permission user list'),
            'users': users,
            'user_groups_remain': user_groups_remain,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionAssetView(PermissionsMixin,
                               SingleObjectMixin,
                               ListView):
    template_name = 'perms/asset_permission_asset.html'
    context_object_name = 'asset_permission'
    paginate_by = settings.DISPLAY_PER_PAGE
    object = None
    permission_classes = [IsOrgAdmin]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetPermission.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = list(self.object.get_all_assets())
        return queryset

    def get_context_data(self, **kwargs):
        assets = self.object.assets.all().values_list('id', flat=True)
        assets = [str(i) for i in assets]
        context = {
            'app': _('Perms'),
            'assets': assets,
            'action': _('Asset permission asset list'),
            'system_users_remain': SystemUser.objects.exclude(
                granted_by_permissions=self.object
            ),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
