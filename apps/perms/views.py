# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals, absolute_import

from django.utils.translation import ugettext as _
from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy

from common.utils import get_object_or_none
from .hands import AdminUserRequiredMixin, Node
from .models import AssetPermission, NodePermission
from .forms import AssetPermissionForm


class AssetPermissionListView(AdminUserRequiredMixin, ListView):
    model = NodePermission
    context_object_name = 'asset_permission_list'
    template_name = 'perms/asset_permission_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Asset permission list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionCreateView(AdminUserRequiredMixin, CreateView):
    model = NodePermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy('perms:asset-permission-list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        node_id = self.request.GET.get("node_id")
        node = get_object_or_none(Node, id=node_id)
        if not node:
            node = Node.root()
        form['node'].initial = node
        return form

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create asset permission'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionUpdateView(AdminUserRequiredMixin, UpdateView):
    model = NodePermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy("perms:asset-permission-list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        form['node'].initial = form.instance.node
        return form

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


