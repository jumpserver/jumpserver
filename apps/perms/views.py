# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals, absolute_import

from django.utils.translation import ugettext as _
from django.conf import settings
from django.db.models import Q
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin

from .hands import AdminUserRequiredMixin, User, UserGroup
from .models import AssetPermission
from .forms import AssetPermissionForm


class AssetPermissionListView(AdminUserRequiredMixin, ListView):
    model = AssetPermission
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'asset_permission_list'
    template_name = 'perms/asset_permission_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Asset permission list'),
            'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(AssetPermissionListView, self).get_context_data(**kwargs)

    def get_queryset(self):
        # Todo: Default order by lose asset connection num
        self.queryset = super(AssetPermissionListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.sort = sort = self.request.GET.get('sort', '-date_created')

        if keyword:
            self.queryset = self.queryset.filter(Q(users__name__icontains=keyword) |
                                                 Q(users__username__icontains=keyword) |
                                                 Q(user_groups__name__icontains=keyword) |
                                                 Q(assets__ip__icontains=keyword) |
                                                 Q(assets__hostname__icontains=keyword) |
                                                 Q(system_users__username_icontains=keyword) |
                                                 Q(system_users__name_icontains=keyword) |
                                                 Q(asset_groups__name__icontains=keyword) |
                                                 Q(comment__icontains=keyword))

        if sort:
            self.queryset = self.queryset.order_by(sort)
        return self.queryset


class AssetPermissionCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy('perms:asset-permission-list')
    success_message = _('Create asset permission <a href="%s"> %s </a> successfully.')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create asset permission'),
        }
        kwargs.update(context)
        return super(AssetPermissionCreateView, self).get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        return self.success_message % (
            reverse_lazy('perms:asset-permission-detail', kwargs={'pk': self.object.pk}),
            self.object.name,
        )


class AssetPermissionUpdateView(AdminUserRequiredMixin, UpdateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_message = _('Update asset permission <a href="%s"> %s </a> successfully.')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Update asset permission')
        }
        kwargs.update(context)
        return super(AssetPermissionUpdateView, self).get_context_data(**kwargs)

    def get_success_url(self):
        success_url = reverse_lazy('perms:asset-permission-detail', kwargs={'pk': self.object.pk})
        return success_url


class AssetPermissionDetailView(AdminUserRequiredMixin, DetailView):
    template_name = 'assets/system_user_detail.html'
    context_object_name = 'system_user'
    model = AssetPermission

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('System user detail')
        }
        kwargs.update(context)
        return super(AssetPermissionDetailView, self).get_context_data(**kwargs)


class AssetPermissionDeleteView(AdminUserRequiredMixin, DeleteView):
    model = AssetPermission
    template_name = 'perms/delete_confirm.html'
    success_url = reverse_lazy('perms:asset-permission-list')
