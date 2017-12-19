# ~*~ coding: utf-8 ~*~

from django.contrib import messages
from django.shortcuts import redirect, reverse
from django.utils.translation import ugettext as _
from django.db import transaction
from django.views.generic import TemplateView, ListView, FormView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin

from ..forms import SystemUserForm, SystemUserUpdateForm, SystemUserAuthForm
from ..models import SystemUser, Cluster
from ..hands import AdminUserRequiredMixin


__all__ = ['SystemUserCreateView', 'SystemUserUpdateView',
           'SystemUserDetailView', 'SystemUserDeleteView',
           'SystemUserAssetView', 'SystemUserListView',
           ]


class SystemUserListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/system_user_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('System user list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SystemUserCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = SystemUser
    form_class = SystemUserForm
    template_name = 'assets/system_user_create.html'
    success_url = reverse_lazy('assets:system-user-list')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        return super(SystemUserCreateView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create system user'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        url = reverse('assets:system-user-detail', kwargs={'pk': self.object.pk})
        success_message = _(
            'Create system user <a href="{url}">{name}</a> '
            'successfully.'.format(url=url, name=self.object.name)
        )

        return success_message


class SystemUserUpdateView(AdminUserRequiredMixin, UpdateView):
    model = SystemUser
    form_class = SystemUserUpdateForm
    template_name = 'assets/system_user_update.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update system user')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        success_url = reverse_lazy('assets:system-user-detail',
                                   kwargs={'pk': self.object.pk})
        return success_url


class SystemUserDetailView(AdminUserRequiredMixin, DetailView):
    template_name = 'assets/system_user_detail.html'
    context_object_name = 'system_user'
    model = SystemUser

    def get_context_data(self, **kwargs):
        cluster_remain = Cluster.objects.exclude(systemuser=self.object)
        context = {
            'app': _('Assets'),
            'action': _('System user detail'),
            'cluster_remain': cluster_remain,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SystemUserDeleteView(AdminUserRequiredMixin, DeleteView):
    model = SystemUser
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('assets:system-user-list')


class SystemUserAssetView(AdminUserRequiredMixin, DetailView):
    model = SystemUser
    template_name = 'assets/system_user_asset.html'
    context_object_name = 'system_user'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'assets',
            'action': 'System user asset',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
