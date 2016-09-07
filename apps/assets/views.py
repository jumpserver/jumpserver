# coding:utf-8
from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, ListView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.conf import settings
from django.db.models import Q
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView, SingleObjectMixin

from .models import Asset, AssetGroup, IDC, AssetExtend, AdminUser, SystemUser
from .forms import AssetForm, AssetGroupForm, IDCForm
from .hands import AdminUserRequiredMixin


class AssetCreateView(CreateView):
    model = Asset
    form_class = AssetForm
    template_name = 'assets/asset_create.html'
    success_url = reverse_lazy('assets:asset-list')

    def form_invalid(self, form):
        print(form.errors)
        return super(AssetCreateView, self).form_invalid(form)


class AssetUpdateView(UpdateView):
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


class AssetGroupCreateView(AdminUserRequiredMixin, CreateView):
    model = AssetGroup
    form_class = AssetGroupForm
    template_name = 'assets/asset_group_create.html'
    success_url = reverse_lazy('assets:asset-group-list')

    # Todo: Asset group create template select assets so hard, need be resolve next

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create asset group'),
            'assets': Asset.objects.all(),
        }
        kwargs.update(context)
        return super(AssetGroupCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        print(form.data)
        return super(AssetGroupCreateView, self).form_valid(form)


class AssetGroupListView(AdminUserRequiredMixin, ListView):
    model = AssetGroup
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'asset_group_list'
    template_name = 'assets/asset_group_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Asset group list'),
            'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(AssetGroupListView, self).get_context_data(**kwargs)

    def get_queryset(self):
        self.queryset = super(AssetGroupListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.sort = sort = self.request.GET.get('sort', '-date_created')

        if keyword:
            self.queryset = self.queryset.filter(Q(name__icontains=keyword) |
                                                 Q(comment__icontains=keyword))

        if sort:
            self.queryset = self.queryset.order_by(sort)
        return self.queryset


class AssetGroupDetailView(SingleObjectMixin, AdminUserRequiredMixin, ListView):
    template_name = 'assets/asset_group_detail.html'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetGroup.objects.all())
        return super(AssetGroupDetailView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return self.object.assets.all()

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Asset group detail'),
            'asset_group': self.object,
        }
        kwargs.update(context)
        return super(AssetGroupDetailView, self).get_context_data(**kwargs)


class AssetGroupUpdateView(AdminUserRequiredMixin, UpdateView):
    model = AssetGroup
    form_class = AssetGroupForm
    template_name = 'assets/asset_group_create.html'
    success_url = reverse_lazy('assets:asset-group-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create asset group'),
            'assets': Asset.objects.all(),
        }
        kwargs.update(context)
        return super(AssetGroupUpdateView, self).get_context_data(**kwargs)


class AssetGroupDeleteView(AdminUserRequiredMixin, DeleteView):
    template_name = 'assets/delete_confirm.html'
    model = AssetGroup
    success_url = reverse_lazy('assets:asset-group-list')


class IDCListView(AdminUserRequiredMixin, ListView):
    model = IDC
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'idc_list'
    template_name = 'assets/idc_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('IDC list'),
            'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(IDCListView, self).get_context_data(**kwargs)

    def get_queryset(self):
        self.queryset = super(IDCListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.sort = sort = self.request.GET.get('sort', '-date_created')

        if keyword:
            self.queryset = self.queryset.filter(Q(name__icontains=keyword) |
                                                 Q(comment__icontains=keyword))

        if sort:
            self.queryset = self.queryset.order_by(sort)
        return self.queryset


class IDCCreateView(AdminUserRequiredMixin, CreateView):
    model = IDC
    form_class = IDCForm
    template_name = 'assets/idc_create.html'
    success_url = reverse_lazy('assets:idc-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': 'assets',
            'action': 'Create IDC'
        }
        kwargs.update(context)
        return super(IDCCreateView, self).get_context_data(**kwargs)


class IDCUpdateView(AdminUserRequiredMixin, UpdateView):
    pass


class IDCDetailView(AdminUserRequiredMixin, DetailView):
    pass


class IDCDeleteView(AdminUserRequiredMixin, DeleteView):
    pass


class AdminUserListView(AdminUserRequiredMixin, ListView):
    model = AdminUser
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'admin_user_list'
    template_name = 'assets/admin_user_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Admin user list'),
            'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(AdminUserListView, self).get_context_data(**kwargs)

    def get_queryset(self):
        # Todo: Default group by lose asset connection num
        self.queryset = super(AdminUserListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.sort = sort = self.request.GET.get('sort', '-date_created')

        if keyword:
            self.queryset = self.queryset.filter(Q(name__icontains=keyword) |
                                                 Q(comment__icontains=keyword))

        if sort:
            self.queryset = self.queryset.order_by(sort)
        return self.queryset


class AdminUserCreateView(AdminUserRequiredMixin, CreateView):
    pass


class AdminUserUpdateView(AdminUserRequiredMixin, UpdateView):
    pass


class AdminUserDetailView(AdminUserRequiredMixin, DetailView):
    pass


class AdminUserDeleteView(AdminUserRequiredMixin, DeleteView):
    pass
