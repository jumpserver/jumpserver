#  coding: utf-8
#

from django.utils.translation import ugettext as _
from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView, CreateView, UpdateView, DetailView, ListView
)
from django.views.generic.edit import SingleObjectMixin
from django.conf import settings

from common.permissions import PermissionsMixin, IsOrgAdmin
from orgs.utils import current_org

from ..hands import RemoteApp, UserGroup, SystemUser
from ..models import RemoteAppPermission
from ..forms import RemoteAppPermissionCreateUpdateForm


__all__ = [
    'RemoteAppPermissionListView', 'RemoteAppPermissionCreateView',
    'RemoteAppPermissionUpdateView', 'RemoteAppPermissionDetailView',
    'RemoteAppPermissionUserView', 'RemoteAppPermissionRemoteAppView'
]


class RemoteAppPermissionListView(PermissionsMixin, TemplateView):
    template_name = 'perms/remote_app_permission_list.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('RemoteApp permission list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class RemoteAppPermissionCreateView(PermissionsMixin, CreateView):
    template_name = 'perms/remote_app_permission_create_update.html'
    model = RemoteAppPermission
    form_class = RemoteAppPermissionCreateUpdateForm
    success_url = reverse_lazy('perms:remote-app-permission-list')
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create RemoteApp permission'),
            'type': 'create'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class RemoteAppPermissionUpdateView(PermissionsMixin, UpdateView):
    template_name = 'perms/remote_app_permission_create_update.html'
    model = RemoteAppPermission
    form_class = RemoteAppPermissionCreateUpdateForm
    success_url = reverse_lazy('perms:remote-app-permission-list')
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Update RemoteApp permission'),
            'type': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class RemoteAppPermissionDetailView(PermissionsMixin, DetailView):
    template_name = 'perms/remote_app_permission_detail.html'
    model = RemoteAppPermission
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('RemoteApp permission detail'),
            'system_users_remain': SystemUser.objects.exclude(
                granted_by_remote_app_permissions=self.object
            ),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class RemoteAppPermissionUserView(PermissionsMixin,
                                  SingleObjectMixin,
                                  ListView):
    template_name = 'perms/remote_app_permission_user.html'
    context_object_name = 'remote_app_permission'
    paginate_by = settings.DISPLAY_PER_PAGE
    object = None
    permission_classes = [IsOrgAdmin]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(
            queryset=RemoteAppPermission.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = list(self.object.get_all_users())
        return queryset

    def get_context_data(self, **kwargs):
        user_remain = current_org.get_org_members(exclude=('Auditor',)).exclude(
            remoteapppermission=self.object)
        user_groups_remain = UserGroup.objects.exclude(
            remoteapppermission=self.object)
        context = {
            'app': _('Perms'),
            'action': _('RemoteApp permission user list'),
            'users_remain': user_remain,
            'user_groups_remain': user_groups_remain,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class RemoteAppPermissionRemoteAppView(PermissionsMixin,
                                       SingleObjectMixin,
                                       ListView):
    template_name = 'perms/remote_app_permission_remote_app.html'
    context_object_name = 'remote_app_permission'
    paginate_by = settings.DISPLAY_PER_PAGE
    object = None
    permission_classes = [IsOrgAdmin]

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

