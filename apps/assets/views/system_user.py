# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django.utils.translation import ugettext as _
from django.conf import settings
from django.db import transaction
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin

from .. import forms
from ..models import Asset, AssetGroup, SystemUser
from ..hands import AdminUserRequiredMixin
from perms.utils import associate_system_users_and_assets


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
        return super(SystemUserListView, self).get_context_data(**kwargs)


class SystemUserCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = SystemUser
    form_class = forms.SystemUserForm
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
        return super(SystemUserCreateView, self).get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        url = reverse_lazy('assets:system-user-detail',
                           kwargs={'pk': self.object.pk}),
        success_message = _(
            'Create system user <a href="{url}">{name}</a> '
            'successfully.'.format(url=url, name=self.object.name)
        )

        return success_message


class SystemUserUpdateView(AdminUserRequiredMixin, UpdateView):
    model = SystemUser
    form_class = forms.SystemUserUpdateForm
    template_name = 'assets/system_user_update.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update system user')
        }
        kwargs.update(context)
        return super(SystemUserUpdateView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        response = super(SystemUserUpdateView, self).form_valid(form)
        system_user = self.object
        assets = system_user.assets.all()
        asset_groups = system_user.asset_groups.all()
        associate_system_users_and_assets([system_user], assets, asset_groups, force=True)
        return response

    def get_success_url(self):
        success_url = reverse_lazy('assets:system-user-detail',
                                   kwargs={'pk': self.object.pk})
        return success_url


class SystemUserDetailView(AdminUserRequiredMixin, DetailView):
    template_name = 'assets/system_user_detail.html'
    context_object_name = 'system_user'
    model = SystemUser

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('System user detail')
        }
        kwargs.update(context)
        return super(SystemUserDetailView, self).get_context_data(**kwargs)


class SystemUserDeleteView(AdminUserRequiredMixin, DeleteView):
    model = SystemUser
    template_name = 'assets/delete_confirm.html'
    success_url = reverse_lazy('assets:system-user-list')


class SystemUserAssetView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    template_name = 'assets/system_user_asset.html'
    context_object_name = 'system_user'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=SystemUser.objects.all())
        return super(SystemUserAssetView, self).get(request, *args, **kwargs)

    def get_asset_groups(self):
        return self.object.asset_groups.all()

    # Todo: queryset default order by connectivity, need ops support
    def get_queryset(self):
        return list(self.object.get_assets())

    def get_context_data(self, **kwargs):
        asset_groups = self.get_asset_groups()
        assets = self.get_queryset()
        context = {
            'app': 'assets',
            'action': 'System user asset',
            'assets_remain': [asset for asset in Asset.objects.all() if asset not in assets],
            'asset_groups': asset_groups,
            'asset_groups_remain': [asset_group for asset_group in AssetGroup.objects.all()
                                    if asset_group not in asset_groups]
        }
        kwargs.update(context)
        return super(SystemUserAssetView, self).get_context_data(**kwargs)






