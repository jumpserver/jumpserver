# coding: utf-8
#

from django.utils.translation import ugettext as _
from django.db.models import Q

from orgs.utils import set_to_root_org
from ..models import DatabaseAppPermission
from common.tree import TreeNode
from applications.models import DatabaseApp
from assets.models import SystemUser


__all__ = [
    'DatabaseAppPermissionUtil',
    'construct_database_apps_tree_root',
    'parse_database_app_to_tree_node'
]


def get_user_database_app_permissions(user, include_group=True):
    if include_group:
        groups = user.groups.all()
        arg = Q(users=user) | Q(user_groups__in=groups)
    else:
        arg = Q(users=user)
    return DatabaseAppPermission.objects.all().valid().filter(arg)


def get_user_group_database_app_permission(user_group):
    return DatabaseAppPermission.objects.all().valid().filter(
        user_group=user_group
    )


class DatabaseAppPermissionUtil:
    get_permissions_map = {
        'User': get_user_database_app_permissions,
        'UserGroup': get_user_group_database_app_permission
    }

    def __init__(self, obj):
        self.object = obj
        self.change_org_if_need()

    @staticmethod
    def change_org_if_need():
        set_to_root_org()

    @property
    def permissions(self):
        obj_class = self.object.__class__.__name__
        func = self.get_permissions_map[obj_class]
        _permissions = func(self.object)
        return _permissions

    def get_database_apps(self):
        database_apps = DatabaseApp.objects.filter(
            granted_by_permissions__in=self.permissions
        ).distinct()
        return database_apps

    def get_database_app_system_users(self, database_app):
        queryset = self.permissions
        kwargs = {'database_apps': database_app}
        queryset = queryset.filter(**kwargs)
        system_users_ids = queryset.values_list('system_users', flat=True)
        system_users_ids = system_users_ids.distinct()
        system_users = SystemUser.objects.filter(id__in=system_users_ids)
        system_users = system_users.order_by('-priority')
        return system_users


def construct_database_apps_tree_root():
    tree_root = {
        'id': 'ID_DATABASE_APP_ROOT',
        'name': _('DatabaseApp'),
        'title': 'DatabaseApp',
        'pId': '',
        'open': False,
        'isParent': True,
        'iconSkin': '',
        'meta': {'type': 'database_app'}
    }
    return TreeNode(**tree_root)


def parse_database_app_to_tree_node(parent, database_app):
    pid = parent.id if parent else ''
    tree_node = {
        'id': database_app.id,
        'name': database_app.name,
        'title': database_app.name,
        'pId': pid,
        'open': False,
        'isParent': False,
        'iconSkin': 'file',
        'meta': {'type': 'database_app'}
    }
    return TreeNode(**tree_node)
