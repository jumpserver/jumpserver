# coding: utf-8
#

from django.utils.translation import ugettext as _
from django.db.models import Q

from orgs.utils import set_to_root_org
from ..models import K8sAppPermission
from common.tree import TreeNode
from applications.models import K8sApp
from assets.models import SystemUser


def get_user_k8s_app_permissions(user, include_group=True):
    if include_group:
        groups = user.groups.all()
        arg = Q(users=user) | Q(user_groups__in=groups)
    else:
        arg = Q(users=user)
    return K8sAppPermission.objects.all().valid().filter(arg)


def get_user_group_k8s_app_permission(user_group):
    return K8sAppPermission.objects.all().valid().filter(
        user_groups=user_group
    )


class K8sAppPermissionUtil:
    get_permissions_map = {
        'User': get_user_k8s_app_permissions,
        'UserGroup': get_user_group_k8s_app_permission
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

    def get_k8s_apps(self):
        k8s_apps = K8sApp.objects.filter(
            granted_by_permissions__in=self.permissions
        ).distinct()
        return k8s_apps

    def get_k8s_app_system_users(self, k8s_app):
        queryset = self.permissions
        kwargs = {'k8s_apps': k8s_app}
        queryset = queryset.filter(**kwargs)
        system_users_ids = queryset.values_list('system_users', flat=True)
        system_users_ids = system_users_ids.distinct()
        system_users = SystemUser.objects.filter(id__in=system_users_ids)
        system_users = system_users.order_by('-priority')
        return system_users


def construct_k8s_apps_tree_root():
    tree_root = {
        'id': 'ID_K8S_APP_ROOT',
        'name': _('KubernetesApp'),
        'title': 'K8sApp',
        'pId': '',
        'open': False,
        'isParent': True,
        'iconSkin': '',
        'meta': {'type': 'k8s_app'}
    }
    return TreeNode(**tree_root)


def parse_k8s_app_to_tree_node(parent, k8s_app):
    pid = parent.id if parent else ''
    tree_node = {
        'id': k8s_app.id,
        'name': k8s_app.name,
        'title': k8s_app.name,
        'pId': pid,
        'open': False,
        'isParent': False,
        'iconSkin': 'file',
        'meta': {'type': 'k8s_app'}
    }
    return TreeNode(**tree_node)
