# coding:utf-8
from __future__ import absolute_import, unicode_literals
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView, SingleObjectMixin
from .. import forms
from ..models import Asset, AssetGroup, AdminUser, Cluster, SystemUser
from ..hands import AdminUserRequiredMixin


__all__ = ['ClusterListView', 'ClusterCreateView', 'ClusterUpdateView',
           'ClusterDetailView', 'ClusterDeleteView', 'ClusterAssetsView']


class ClusterListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/cluster_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Cluster list'),
            # 'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(ClusterListView, self).get_context_data(**kwargs)


class ClusterCreateView(AdminUserRequiredMixin, CreateView):
    model = Cluster
    form_class = forms.ClusterForm
    template_name = 'assets/cluster_create_update.html'
    success_url = reverse_lazy('assets:cluster-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('assets'),
            'action': _('Create Cluster'),
        }
        kwargs.update(context)
        return super(ClusterCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        cluster = form.save(commit=False)
        cluster.created_by = self.request.user.username or 'System'
        cluster.save()
        return super(ClusterCreateView, self).form_valid(form)


class ClusterUpdateView(AdminUserRequiredMixin, UpdateView):
    model = Cluster
    form_class = forms.ClusterForm
    template_name = 'assets/cluster_create_update.html'
    context_object_name = 'cluster'
    success_url = reverse_lazy('assets:cluster-list')

    def form_valid(self, form):
        cluster = form.save(commit=False)
        cluster.save()
        return super(ClusterUpdateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('assets'),
            'action': _('Update Cluster'),
        }
        kwargs.update(context)
        return super(ClusterUpdateView, self).get_context_data(**kwargs)


class ClusterDetailView(AdminUserRequiredMixin, DetailView):
    model = Cluster
    template_name = 'assets/cluster_detail.html'
    context_object_name = 'cluster'


class ClusterAssetsView(AdminUserRequiredMixin, DetailView):
    model = Cluster
    template_name = 'assets/cluster_assets.html'
    context_object_name = 'cluster'

    def get_context_data(self, **kwargs):
        assets_remain = Asset.objects.exclude(id__in=self.object.assets.all())

        context = {
            'app': _('Assets'),
            'action': _('Asset detail'),
            'groups': AssetGroup.objects.all(),
            'system_users': SystemUser.objects.all(),
            'assets_remain': assets_remain,
            'assets': [asset for asset in Asset.objects.all() if asset not in assets_remain],
        }
        kwargs.update(context)
        return super(ClusterAssetsView, self).get_context_data(**kwargs)


class ClusterDeleteView(AdminUserRequiredMixin, DeleteView):
    model = Cluster
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('assets:cluster-list')
