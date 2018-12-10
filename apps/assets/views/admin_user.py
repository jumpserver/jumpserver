# coding:utf-8
from __future__ import absolute_import, unicode_literals
from django.utils.translation import ugettext as _
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin

from common.const import create_success_msg, update_success_msg
from .. import forms
from ..models import AdminUser, Node
from common.permissions import AdminUserRequiredMixin

__all__ = [
    'AdminUserCreateView', 'AdminUserDetailView',
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
    success_message = create_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create admin user')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdminUserUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = AdminUser
    form_class = forms.AdminUserForm
    template_name = 'assets/admin_user_create_update.html'
    success_url = reverse_lazy('assets:admin-user-list')
    success_message = update_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update admin user'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdminUserDetailView(AdminUserRequiredMixin, DetailView):
    model = AdminUser
    template_name = 'assets/admin_user_detail.html'
    context_object_name = 'admin_user'
    object = None

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Admin user detail'),
            'nodes': Node.objects.all()
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdminUserAssetsView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    paginate_by = settings.DISPLAY_PER_PAGE
    template_name = 'assets/admin_user_assets.html'
    context_object_name = 'admin_user'
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AdminUser.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        self.queryset = self.object.asset_set.all()
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Admin user detail'),
            "total_amount": len(self.queryset),
            'unreachable_amount': len([asset for asset in self.queryset if asset.connectivity is False])
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdminUserDeleteView(AdminUserRequiredMixin, DeleteView):
    model = AdminUser
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('assets:admin-user-list')


