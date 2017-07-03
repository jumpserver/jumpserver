# coding:utf-8
from __future__ import absolute_import, unicode_literals
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView, SingleObjectMixin
from .. import forms
from ..models import Asset, AssetGroup, AdminUser, IDC, SystemUser
from ..hands import AdminUserRequiredMixin


__all__ = ['IDCListView', 'IDCCreateView', 'IDCUpdateView',
           'IDCDetailView', 'IDCDeleteView', 'IDCAssetsView']


class IDCListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/idc_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('IDC list'),
            # 'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(IDCListView, self).get_context_data(**kwargs)


class IDCCreateView(AdminUserRequiredMixin, CreateView):
    model = IDC
    form_class = forms.IDCForm
    template_name = 'assets/idc_create_update.html'
    success_url = reverse_lazy('assets:idc-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('assets'),
            'action': _('Create IDC'),
        }
        kwargs.update(context)
        return super(IDCCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        idc = form.save(commit=False)
        idc.created_by = self.request.user.username or 'System'
        idc.save()
        return super(IDCCreateView, self).form_valid(form)


class IDCUpdateView(AdminUserRequiredMixin, UpdateView):
    model = IDC
    form_class = forms.IDCForm
    template_name = 'assets/idc_create_update.html'
    context_object_name = 'idc'
    success_url = reverse_lazy('assets:idc-list')

    def form_valid(self, form):
        idc = form.save(commit=False)
        idc.save()
        return super(IDCUpdateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('assets'),
            'action': _('Update IDC'),
        }
        kwargs.update(context)
        return super(IDCUpdateView, self).get_context_data(**kwargs)


class IDCDetailView(AdminUserRequiredMixin, DetailView):
    model = IDC
    template_name = 'assets/idc_detail.html'
    context_object_name = 'idc'


class IDCAssetsView(AdminUserRequiredMixin, DetailView):
    model = IDC
    template_name = 'assets/idc_assets.html'
    context_object_name = 'idc'

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
        return super(IDCAssetsView, self).get_context_data(**kwargs)


class IDCDeleteView(AdminUserRequiredMixin, DeleteView):
    model = IDC
    template_name = 'assets/delete_confirm.html'
    success_url = reverse_lazy('assets:idc-list')
