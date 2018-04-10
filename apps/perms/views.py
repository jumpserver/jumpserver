# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals, absolute_import

from django.utils.translation import ugettext as _
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from django.conf import settings

from common.utils import get_object_or_none
from .hands import AdminUserRequiredMixin, Node, Asset
from .models import AssetPermission
from .forms import AssetPermissionForm


class AssetPermissionListView(AdminUserRequiredMixin, ListView):
    model = AssetPermission
    template_name = 'perms/asset_permission_list.html'
    paginate_by = settings.DISPLAY_PER_PAGE
    user = user_group = asset = node = system_user = q = ""

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
        nodes_id = self.request.GET.get("nodes").split(",")
        assets_id = self.request.GET.get("assets").split(",")

        if nodes_id:
            nodes = Node.objects.filter(id__in=nodes_id)
            form['nodes'].initial = nodes
        if assets_id:
            assets = Asset.objects.filter(id__in=assets_id)
            form['assets'].initial = assets
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
            'action': _('Update asset permission')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionDeleteView(AdminUserRequiredMixin, DeleteView):
    model = AssetPermission
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('perms:asset-permission-list')


