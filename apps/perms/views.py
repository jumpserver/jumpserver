# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals, absolute_import

from django.utils.translation import ugettext as _
from django.conf import settings
from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic.edit import DeleteView, FormView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.contrib import messages

from .hands import AdminUserRequiredMixin, User, UserGroup, SystemUser, \
    Asset, AssetGroup
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
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class MessageMixin:
    def form_valid(self, form):
        response = super().form_valid(form)
        errors = self.object.check_system_user_in_assets()
        if errors:
            message = self.get_warning_messages(errors)
            messages.warning(self.request, message)
        else:
            message = self.get_success_message(form.cleaned_data)
            messages.success(self.request, message)

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return response

    @staticmethod
    def get_warning_messages(errors):
        message = "<b><i class='fa fa-warning'></i>WARNING: System user " \
                  "should in behind clusters, so that " \
                  "system user cat auto push to the cluster assets:</b>  <br>"
        for system_user, clusters in errors.items():
            message += "    >>> {}: {} ".format(system_user.name, ", ".join((cluster.name for cluster in clusters)))
        return message

    def get_success_message(self, cleaned_data):
        url = reverse_lazy('perms:asset-permission-detail',
                           kwargs={'pk': self.object.pk})
        success_message = _(
            'Create asset permission <a href="{url}"> {name} </a> '
            'successfully.'.format(url=url, name=self.object.name))
        return success_message


class AssetPermissionCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy('perms:asset-permission-list')
    warning = None

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create asset permission'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        url = reverse_lazy(
            'perms:asset-permission-detail',
            kwargs={'pk': self.object.pk}
        )
        success_message = _(
            'Create asset permission <a href="{url}"> {name} </a> '
            'success.'.format(url=url, name=self.object.name)
        )
        return success_message


class AssetPermissionUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = AssetPermission
    form_class = AssetPermissionForm
    template_name = 'perms/asset_permission_create_update.html'
    success_url = reverse_lazy("perms:asset-permission-list")

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Update asset permission')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        url = reverse_lazy(
            'perms:asset-permission-detail',
            kwargs={'pk': self.object.pk}
        )
        success_message = _(
            'Update asset permission <a href="{url}"> {name} </a> '
            'success.'.format(url=url, name=self.object.name)
        )
        return success_message


class AssetPermissionDetailView(AdminUserRequiredMixin, DetailView):
    template_name = 'perms/asset_permission_detail.html'
    context_object_name = 'asset_permission'
    model = AssetPermission

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Asset permission detail'),
            'system_users_remain': [
                system_user for system_user in SystemUser.objects.all()
                if system_user not in self.object.system_users.all()],
            'system_users': self.object.system_users.all(),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionDeleteView(AdminUserRequiredMixin, DeleteView):
    model = AssetPermission
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('perms:asset-permission-list')


class AssetPermissionUserView(AdminUserRequiredMixin,
                              SingleObjectMixin,
                              ListView):
    template_name = 'perms/asset_permission_user.html'
    context_object_name = 'asset_permission'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetPermission.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.object.get_granted_users()
        return queryset

    def get_context_data(self, **kwargs):
        users_granted = self.get_queryset()
        groups_granted = self.object.user_groups.all()
        context = {
            'app': _('Perms'),
            'action': _('Asset permission user list'),
            'users_remain': User.objects.exclude(id__in=[user.id for user in users_granted]),
            'user_groups': self.object.user_groups.all(),
            'user_groups_remain': UserGroup.objects.exclude(id__in=[group.id for group in groups_granted])
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetPermissionAssetView(AdminUserRequiredMixin,
                               SingleObjectMixin,
                               ListView):
    template_name = 'perms/asset_permission_asset.html'
    context_object_name = 'asset_permission'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetPermission.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.object.get_granted_assets()
        return queryset

    def get_context_data(self, **kwargs):
        assets_granted = self.get_queryset()
        groups_granted = self.object.asset_groups.all()
        context = {
            'app': _('Perms'),
            'action': _('Asset permission asset list'),
            'assets_remain': Asset.objects.exclude(id__in=[asset.id for asset in assets_granted]),
            'asset_groups': self.object.asset_groups.all(),
            'asset_groups_remain': AssetGroup.objects.exclude(id__in=[group.id for group in groups_granted])
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
