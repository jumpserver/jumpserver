# coding:utf-8
from __future__ import absolute_import, unicode_literals
from django.utils.translation import ugettext as _
from django.conf import settings
from django.views.generic import TemplateView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin

from .. import forms
from ..models import Asset, AssetGroup, AdminUser, Cluster, SystemUser
from ..hands import AdminUserRequiredMixin

__all__ = ['AdminUserCreateView', 'AdminUserDetailView',
           'AdminUserDeleteView', 'AdminUserListView',
           'AdminUserUpdateView', 'AdminUserAssetsView',
           ]


class AdminUserListView(AdminUserRequiredMixin, TemplateView):
    model = AdminUser
    template_name = 'assets/admin_user_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Admin user list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdminUserCreateView(AdminUserRequiredMixin,
                          SuccessMessageMixin,
                          CreateView):
    model = AdminUser
    form_class = forms.AdminUserForm
    template_name = 'assets/admin_user_create_update.html'
    success_url = reverse_lazy('assets:admin-user-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': 'assets',
            'action': 'Create admin user'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        success_message = _(
            'Create admin user <a href="{url}">{name}</a> successfully.'.format(
                url=reverse_lazy('assets:admin-user-detail',
                                 kwargs={'pk': self.object.pk}),
                name=self.object.name,
            ))
        return success_message


class AdminUserUpdateView(AdminUserRequiredMixin, UpdateView):
    model = AdminUser
    form_class = forms.AdminUserForm
    template_name = 'assets/admin_user_create_update.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'assets',
            'action': 'Update admin user'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        success_url = reverse_lazy('assets:admin-user-detail',
                                   kwargs={'pk': self.object.pk})
        return success_url


class AdminUserDetailView(AdminUserRequiredMixin, DetailView):
    model = AdminUser
    template_name = 'assets/admin_user_detail.html'
    context_object_name = 'admin_user'
    object = None

    def get_context_data(self, **kwargs):
        cluster_remain = Cluster.objects.exclude(admin_user=self.object)
        context = {
            'app': 'assets',
            'action': 'Admin user detail',
            'cluster_remain': cluster_remain,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdminUserAssetsView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    template_name = 'assets/admin_user_assets.html'
    context_object_name = 'admin_user'
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AdminUser.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = []
        for cluster in self.object.cluster_set.all():
            queryset.extend(list(cluster.assets.all()))
        self.queryset = queryset
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': 'assets',
            'action': 'Admin user detail',
            "total_amount": len(self.queryset),
            'unreachable_amount': len([asset for asset in self.queryset if asset.is_connective() is False])
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdminUserDeleteView(AdminUserRequiredMixin, DeleteView):
    model = AdminUser
    template_name = 'assets/delete_confirm.html'
    success_url = reverse_lazy('assets:admin-user-list')


