# coding:utf-8
from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.shortcuts import get_object_or_404, reverse, redirect
from django.contrib.messages.views import SuccessMessageMixin

from common.const import create_success_msg, update_success_msg
from .. import forms
from ..models import Asset, AssetGroup, AdminUser, Cluster, SystemUser
from ..hands import AdminUserRequiredMixin


__all__ = [
    'AssetGroupCreateView', 'AssetGroupDetailView',
    'AssetGroupUpdateView', 'AssetGroupListView',
    'AssetGroupDeleteView',
]


class AssetGroupCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = AssetGroup
    form_class = forms.AssetGroupForm
    template_name = 'assets/asset_group_create.html'
    success_url = reverse_lazy('assets:asset-group-list')
    success_message = create_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create asset group'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        group = form.save()
        group.created_by = self.request.user.username
        group.save()
        return super().form_valid(form)


class AssetGroupListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/asset_group_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Asset group list'),
            'assets': Asset.objects.all(),
            'system_users': SystemUser.objects.all(),
        }
        kwargs.update(context)
        return super(AssetGroupListView, self).get_context_data(**kwargs)


class AssetGroupDetailView(AdminUserRequiredMixin, DetailView):
    model = AssetGroup
    template_name = 'assets/asset_group_detail.html'
    context_object_name = 'asset_group'

    def get_context_data(self, **kwargs):
        assets_remain = Asset.objects.exclude(groups__in=[self.object])
        context = {
            'app': _('Assets'),
            'action': _('Asset group detail'),
            'assets_remain': assets_remain,
            'assets': self.object.assets.all(),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetGroupUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = AssetGroup
    form_class = forms.AssetGroupForm
    template_name = 'assets/asset_group_create.html'
    success_url = reverse_lazy('assets:asset-group-list')
    success_message = update_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create asset group'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetGroupDeleteView(AdminUserRequiredMixin, DeleteView):
    template_name = 'delete_confirm.html'
    model = AssetGroup
    success_url = reverse_lazy('assets:asset-group-list')
