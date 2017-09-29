# coding:utf-8
from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.shortcuts import get_object_or_404, reverse, redirect

from .. import forms
from ..models import Asset, AssetGroup, AdminUser, IDC, SystemUser
from ..hands import AdminOrGroupAdminRequiredMixin


__all__ = ['AssetGroupCreateView', 'AssetGroupDetailView',
           'AssetGroupUpdateView', 'AssetGroupListView',
           'AssetGroupDeleteView',
           ]

class AssetGroupListView(AdminOrGroupAdminRequiredMixin, TemplateView):
    template_name = 'assets/asset_group_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Asset group list'),
            'assets': Asset.objects.all(),
            'system_users': SystemUser.objects.all(),
            'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(AssetGroupListView, self).get_context_data(**kwargs)


class AssetGroupDetailView(AdminOrGroupAdminRequiredMixin, DetailView):
    model = AssetGroup
    template_name = 'assets/asset_group_detail.html'
    context_object_name = 'asset_group'

    def get_context_data(self, **kwargs):
        assets_remain = Asset.objects.exclude(id__in=self.object.assets.all())
        system_users = SystemUser.objects.all()
        system_users_remain = SystemUser.objects.exclude(id__in=system_users)
        is_owner = self.request.user == self.object.creater
        context = {
            'app': _('Assets'),
            'action': _('Asset group detail'),
            'is_owner': is_owner,
            'assets_remain': assets_remain,
            'assets': [asset for asset in Asset.objects.all()
                       if asset not in assets_remain],
            'system_users': system_users,
            'system_users_remain': system_users_remain,
        }
        kwargs.update(context)
        return super(AssetGroupDetailView, self).get_context_data(**kwargs)

class AssetGroupCreateView(AdminOrGroupAdminRequiredMixin, CreateView):
    model = AssetGroup
    form_class = forms.AssetGroupForm
    template_name = 'assets/asset_group_create.html'
    success_url = reverse_lazy('assets:asset-group-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create asset group'),
            'assets_count': 0,
        }
        kwargs.update(context)
        return super(AssetGroupCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        asset_group = form.save()
        assets_id_list = self.request.POST.getlist('assets', [])
        assets = [get_object_or_404(Asset, id=int(asset_id))
                  for asset_id in assets_id_list]
        asset_group.created_by = self.request.user.username or 'Admin'
        asset_group.creater = self.request.user
        asset_group.assets.add(*tuple(assets))
        asset_group.save()
        return super(AssetGroupCreateView, self).form_valid(form)


class AssetGroupUpdateView(AdminOrGroupAdminRequiredMixin, UpdateView):
    model = AssetGroup
    form_class = forms.AssetGroupForm
    template_name = 'assets/asset_group_create.html'
    success_url = reverse_lazy('assets:asset-group-list')

    def dispatch(self, request, *args, **kwargs):
        instance = AssetGroup.objects.get(pk=kwargs.get('pk'))
        if(request.user != instance.creater):
            return redirect(success_url)
        return super(AssetGroupUpdateView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetGroup.objects.all())
        return super(AssetGroupUpdateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        assets_all = self.object.assets.all()
        context = {
            'app': _('Assets'),
            'action': _('Create asset group'),
            'assets_on_list': assets_all,
            'assets_count': len(assets_all),
            'group_id': self.object.id,
        }
        kwargs.update(context)
        return super(AssetGroupUpdateView, self).get_context_data(**kwargs)


class AssetGroupDeleteView(AdminOrGroupAdminRequiredMixin, DeleteView):
    template_name = 'assets/delete_confirm.html'
    model = AssetGroup
    success_url = reverse_lazy('assets:asset-group-list')

    def dispatch(self, request, *args, **kwargs):
        instance = AssetGroup.objects.get(pk=kwargs.get('pk'))
        if(request.user != instance.creater):
            return redirect(reverse('assets:asset-group-list'))
        return super(AssetGroupDeleteView, self).dispatch(request, *args, **kwargs)
