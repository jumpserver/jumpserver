# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf import settings
from django.views.generic.list import ListView, MultipleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.detail import DetailView, SingleObjectMixin

from .hands import AdminUserRequiredMixin
from .utils import *


class SudoListView(AdminUserRequiredMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    model = Asset
    context_object_name = 'asset_list'
    template_name = 'assets/asset_list.html'

    def get_queryset(self):
        queryset = super(AssetListView, self).get_queryset()
        queryset = sorted(queryset, key=self.sorted_by_valid_and_ip)
        return queryset

    @staticmethod
    def sorted_by_valid_and_ip(asset):
        ip_list = int_seq(asset.ip.split('.'))
        ip_list.insert(0, asset.is_valid()[0])
        return ip_list

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'asset list',
            'tag_list': [(i.id,i.name,i.asset_set.all().count())for i in Tag.objects.all().order_by('name')]

        }
        kwargs.update(context)
        return super(AssetListView, self).get_context_data(**kwargs)


class SudoCreateView(AdminUserRequiredMixin,
                     CreateHostAliasMinxin,
                     CreateUserAliasMinxin,
                     CreateCmdAliasMinxin,
                     CreateRunasAliasMinxin,
                     CreateExtralineAliasMinxin,
                     CreateView):
    model = Asset
    tag_type = 'asset'
    form_class = AssetCreateForm
    template_name = 'assets/asset_create.html'
    success_url = reverse_lazy('assets:asset-list')

    def form_valid(self, form):
        asset = form.save()
        asset.created_by = self.request.user.username or 'Admin'
        asset.save()
        return super(AssetCreateView, self).form_valid(form)

    def form_invalid(self, form):
        print(form.errors)
        return super(AssetCreateView, self).form_invalid(form)


    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'Create asset',
        }
        kwargs.update(context)

        return super(AssetCreateView, self).get_context_data(**kwargs)


class SudoUpdateView(AdminUserRequiredMixin,
                     UpdateHostAliasMinxin,
                     UpdateUserAliasMinxin,
                     UpdateCmdAliasMinxin,
                     UpdateRunasAliasMinxin,
                     UpdateExtralineAliasMinxin,
                     UpdateView):
    model = Asset
    form_class = AssetCreateForm
    template_name = 'assets/asset_update.html'
    success_url = reverse_lazy('assets:asset-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'Update asset',
        }
        kwargs.update(context)
        return super(AssetUpdateView, self).get_context_data(**kwargs)

    def form_invalid(self, form):
        print(form.errors)
        return super(AssetUpdateView, self).form_invalid(form)


class SudoDeleteView(DeleteView):
    model = Asset
    template_name = 'assets/delete_confirm.html'
    success_url = reverse_lazy('assets:asset-list')


class SudoDetailView(DetailView):
    model = Asset
    context_object_name = 'asset'
    template_name = 'assets/asset_detail.html'

    def get_context_data(self, **kwargs):
        asset_groups = self.object.groups.all()
        context = {
            'app': 'Assets',
            'action': 'Asset detail',
            'asset_groups_remain': [asset_group for asset_group in AssetGroup.objects.all()
                                   if asset_group not in asset_groups],
            'asset_groups': asset_groups,
        }
        kwargs.update(context)
        return super(AssetDetailView, self).get_context_data(**kwargs)
