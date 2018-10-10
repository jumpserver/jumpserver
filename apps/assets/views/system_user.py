# ~*~ coding: utf-8 ~*~

from django.utils.translation import ugettext as _
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView

from common.const import create_success_msg, update_success_msg
from ..forms import SystemUserForm
from ..models import SystemUser, Node, CommandFilter
from common.permissions import AdminUserRequiredMixin


__all__ = [
    'SystemUserCreateView', 'SystemUserUpdateView',
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
    success_message = create_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create system user'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SystemUserUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = SystemUser
    form_class = SystemUserForm
    template_name = 'assets/system_user_update.html'
    success_url = reverse_lazy('assets:system-user-list')
    success_message = update_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update system user')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SystemUserDetailView(AdminUserRequiredMixin, DetailView):
    template_name = 'assets/system_user_detail.html'
    context_object_name = 'system_user'
    model = SystemUser

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('System user detail'),
            'cmd_filters_remain': CommandFilter.objects.exclude(system_users=self.object)
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
        nodes_remain = sorted(Node.objects.exclude(systemuser=self.object), reverse=True)
        context = {
            'app': _('assets'),
            'action': _('System user asset'),
            'nodes_remain': nodes_remain
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
