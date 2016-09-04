# coding:utf-8
from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, ListView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView

from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from .models import Asset, AssetGroup, IDC, AssetExtend
from .forms import AssetForm, AssetGroupForm

from .utils import AdminUserRequiredMixin


class AssetAddView(CreateView):
    model = Asset
    form_class = AssetForm
    template_name = 'assets/asset_add.html'
    success_url = reverse_lazy('assets:asset-list')

    def form_invalid(self, form):
        print(form.errors)
        return super(AssetAddView, self).form_invalid(form)


class AssetEditView(UpdateView):
    pass


class AssetDeleteView(DeleteView):
    model = Asset
    success_url = reverse_lazy('assets:asset-list')


class AssetListView(ListView):
    model = Asset
    context_object_name = 'assets'
    template_name = 'assets/asset_list.html'


class AssetDetailView(DetailView):
    model = Asset
    context_object_name = 'asset'
    template_name = 'assets/asset_detail.html'


class AssetGroupAddView(CreateView):
    model = AssetGroup
    form_class = AssetGroupForm
    template_name = 'assets/assetgroup_add.html'
    success_url = reverse_lazy('assets:assetgroup-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create asset group'),
            'assets': Asset.objects.all(),
        }
        kwargs.update(context)
        return super(AssetGroupAddView, self).get_context_data(**kwargs)


class AssetGroupListView(ListView):
    model = AssetGroup
    context_object_name = 'assetgroups'
    template_name = 'assets/assetgroup_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Asset group list')
        }
        kwargs.update(context)
        return super(AssetGroupListView, self).get_context_data(**kwargs)


class AssetGroupDetailView(DetailView):
    pass


class AssetGroupEditView(UpdateView):
    pass


class AssetGroupDeleteView(DeleteView):
    pass
