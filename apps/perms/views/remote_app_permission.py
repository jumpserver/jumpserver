#  coding: utf-8
#

from django.utils.translation import ugettext as _
from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView, CreateView, UpdateView, DetailView, ListView
)
from django.views.generic.edit import SingleObjectMixin
from django.conf import settings

from common.permissions import AdminUserRequiredMixin
from orgs.utils import current_org
from users.models import UserGroup
from assets.models import RemoteApp

from ..models import RemoteAppPermission
from ..forms import RemoteAppPermissionCreateUpdateForm


__all__ = [
    'RemoteAppPermissionListView', 'RemoteAppPermissionCreateView',
    'RemoteAppPermissionUpdateView', 'RemoteAppPermissionDetailView',
    'RemoteAppPermissionUserView', 'RemoteAppPermissionRemoteAppView'
]


class RemoteAppPermissionListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'perms/remote_app_permission_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('RemoteApp permission list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class RemoteAppPermissionCreateView(AdminUserRequiredMixin, CreateView):
    template_name = 'perms/remote_app_permission_create_update.html'
    model = RemoteAppPermission
    form_class = RemoteAppPermissionCreateUpdateForm
    success_url = reverse_lazy('perms:remote-app-permission-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create RemoteApp permission'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class RemoteAppPermissionUpdateView(AdminUserRequiredMixin, UpdateView):
    template_name = 'perms/remote_app_permission_create_update.html'
    model = RemoteAppPermission
    form_class = RemoteAppPermissionCreateUpdateForm
    success_url = reverse_lazy('perms:remote-app-permission-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Update RemoteApp permission')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class RemoteAppPermissionDetailView(AdminUserRequiredMixin, DetailView):
    template_name = 'perms/remote_app_permission_detail.html'
    model = RemoteAppPermission

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('RemoteApp permission detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class RemoteAppPermissionUserView(AdminUserRequiredMixin,
                                  SingleObjectMixin,
                                  ListView):
    template_name = 'perms/remote_app_permission_user.html'
    context_object_name = 'remote_app_permission'
    paginate_by = settings.DISPLAY_PER_PAGE
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(
            queryset=RemoteAppPermission.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = list(self.object.get_all_users())
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('RemoteApp permission user list'),
            'users_remain': current_org.get_org_users().exclude(
                remoteapppermission=self.object
            ),
            'user_groups_remain': UserGroup.objects.exclude(
                remoteapppermission=self.object
            )
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class RemoteAppPermissionRemoteAppView(AdminUserRequiredMixin,
                                       SingleObjectMixin,
                                       ListView):
    template_name = 'perms/remote_app_permission_remote_app.html'
    context_object_name = 'remote_app_permission'
    paginate_by = settings.DISPLAY_PER_PAGE
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(
            queryset=RemoteAppPermission.objects.all()
        )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = list(self.object.get_all_remote_apps())
        return queryset

    def get_context_data(self, **kwargs):
        remote_app_granted = self.get_queryset()
        remote_app_remain = RemoteApp.objects.exclude(
            id__in=[a.id for a in remote_app_granted])
        context = {
            'app': _('Perms'),
            'action': _('RemoteApp permission RemoteApp list'),
            'remote_app_remain': remote_app_remain
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

