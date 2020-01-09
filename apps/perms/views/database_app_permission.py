# coding: utf-8
#

from django.utils.translation import ugettext as _

from django.views.generic import (
    TemplateView, CreateView, UpdateView, DetailView, ListView
)
from django.views.generic.edit import SingleObjectMixin
from django.conf import settings

from common.permissions import PermissionsMixin, IsOrgAdmin
from users.models import UserGroup
from applications.models import DatabaseApp
from assets.models import SystemUser

from .. import models, forms


__all__ = [
    'DatabaseAppPermissionListView', 'DatabaseAppPermissionCreateView',
    'DatabaseAppPermissionUpdateView', 'DatabaseAppPermissionDetailView',
    'DatabaseAppPermissionUserView', 'DatabaseAppPermissionDatabaseAppView',
]


class DatabaseAppPermissionListView(PermissionsMixin, TemplateView):
    template_name = 'perms/database_app_permission_list.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('DatabaseApp permission list')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DatabaseAppPermissionCreateView(PermissionsMixin, CreateView):
    template_name = 'perms/database_app_permission_create_update.html'
    model = models.DatabaseAppPermission
    form_class = forms.DatabaseAppPermissionCreateUpdateForm
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Create DatabaseApp permission'),
            'api_action': 'create',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DatabaseAppPermissionUpdateView(PermissionsMixin, UpdateView):
    template_name = 'perms/database_app_permission_create_update.html'
    model = models.DatabaseAppPermission
    form_class = forms.DatabaseAppPermissionCreateUpdateForm
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('Update DatabaseApp permission'),
            'api_action': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DatabaseAppPermissionDetailView(PermissionsMixin, DetailView):
    template_name = 'perms/database_app_permission_detail.html'
    model = models.DatabaseAppPermission
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Perms'),
            'action': _('DatabaseApp permission detail')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DatabaseAppPermissionUserView(PermissionsMixin,
                                    SingleObjectMixin,
                                    ListView):
    template_name = 'perms/database_app_permission_user.html'
    context_object_name = 'database_app_permission'
    paginate_by = settings.DISPLAY_PER_PAGE
    object = None
    permission_classes = [IsOrgAdmin]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=models.DatabaseAppPermission.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = list(self.object.get_all_users())
        return queryset

    def get_context_data(self, **kwargs):
        users = [str(i) for i in self.object.users.all().values_list('id', flat=True)]
        user_groups_remain = UserGroup.objects.exclude(
            databaseapppermission=self.object)
        context = {
            'app': _('Perms'),
            'action': _('DatabaseApp permission user list'),
            'users': users,
            'user_groups_remain': user_groups_remain,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DatabaseAppPermissionDatabaseAppView(PermissionsMixin,
                                           SingleObjectMixin,
                                           ListView):
    template_name = 'perms/database_app_permission_database_app.html'
    context_object_name = 'database_app_permission'
    paginate_by = settings.DISPLAY_PER_PAGE
    object = None
    permission_classes = [IsOrgAdmin]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(
            queryset=models.DatabaseAppPermission.objects.all()
        )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = list(self.object.get_all_database_apps())
        return queryset

    def get_context_data(self, **kwargs):
        database_apps = self.object.get_all_database_apps().values_list('id', flat=True)
        database_apps = [str(i) for i in database_apps]
        system_users_remain = SystemUser.objects\
            .exclude(granted_by_database_app_permissions=self.object)\
            .filter(protocol=SystemUser.PROTOCOL_MYSQL)
        context = {
            'app': _('Perms'),
            'database_apps': database_apps,
            'database_apps_remain': DatabaseApp.objects.exclude(
                granted_by_permissions=self.object
            ),
            'system_users_remain': system_users_remain,
            'action': _('DatabaseApp permission DatabaseApp list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
