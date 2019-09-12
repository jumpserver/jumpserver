#  coding: utf-8
#

from django.db.models import Q

from common.tree import TreeNode
from orgs.utils import set_to_root_org

from ..models import RemoteAppPermission
from ..hands import RemoteApp, SystemUser


__all__ = [
    'RemoteAppPermissionUtil',
    'construct_remote_apps_tree_root',
    'parse_remote_app_to_tree_node',
]


def get_user_remote_app_permissions(user, include_group=True):
    if include_group:
        groups = user.groups.all()
        arg = Q(users=user) | Q(user_groups__in=groups)
    else:
        arg = Q(users=user)
    return RemoteAppPermission.objects.all().valid().filter(arg)


def get_user_group_remote_app_permissions(user_group):
    return RemoteAppPermission.objects.all().valid().filter(
        user_groups=user_group
    )


class RemoteAppPermissionUtil:
    get_permissions_map = {
        "User": get_user_remote_app_permissions,
        "UserGroup": get_user_group_remote_app_permissions,
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

    def get_remote_apps(self):
        remote_apps = RemoteApp.objects.filter(
            granted_by_permissions__in=self.permissions
        )
        return remote_apps

    def get_remote_app_system_users(self, remote_app):
        queryset = self.permissions
        kwargs = {"remote_apps": remote_app}
        queryset = queryset.filter(**kwargs)
        system_users_ids = queryset.values_list('system_users', flat=True)
        system_users_ids = system_users_ids.distinct()
        system_users = SystemUser.objects.filter(id__in=system_users_ids)
        system_users = system_users.order_by('-priority')
        return system_users


def construct_remote_apps_tree_root():
    tree_root = {
        'id': 'ID_REMOTE_APP_ROOT',
        'name': 'RemoteApp',
        'title': 'RemoteApp',
        'pId': '',
        'open': False,
        'isParent': True,
        'iconSkin': '',
        'meta': {'type': 'remote_app'}
    }
    return TreeNode(**tree_root)


def parse_remote_app_to_tree_node(parent, remote_app):
    pid = parent.id if parent else ''
    tree_node = {
        'id': remote_app.id,
        'name': remote_app.name,
        'title': remote_app.name,
        'pId': pid,
        'open': False,
        'isParent': False,
        'iconSkin': 'file',
        'meta': {'type': 'remote_app'}
    }
    return TreeNode(**tree_node)
