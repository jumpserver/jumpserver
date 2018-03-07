# coding: utf-8

from __future__ import absolute_import, unicode_literals
import collections
from django.utils import timezone
from django.utils.translation import ugettext as _
import copy

from common.utils import setattr_bulk, get_logger
from .models import NodePermission

logger = get_logger(__file__)


class NodePermissionUtil:

    @staticmethod
    def get_user_group_permissions(user_group):
        return user_group.nodepermission_set.all() \
            .filter(is_active=True) \
            .filter(date_expired__gt=timezone.now())

    @staticmethod
    def get_system_user_permissions(system_user):
        return system_user.nodepermission_set.all() \
            .filter(is_active=True) \
            .filter(date_expired__gt=timezone.now())

    @classmethod
    def get_user_group_nodes(cls, user_group):
        """
        获取用户组授权的node和系统用户
        :param user_group:
        :return: {"node": set(systemuser1, systemuser2), ..}
        """
        permissions = cls.get_user_group_permissions(user_group)
        nodes_directed = collections.defaultdict(set)

        for perm in permissions:
            nodes_directed[perm.node].add(perm.system_user)

        nodes = copy.deepcopy(nodes_directed)
        for node, system_users in nodes_directed.items():
            for child in node.get_family():
                nodes[child].update(system_users)
        return nodes

    @classmethod
    def get_user_group_nodes_with_assets(cls, user_group):
        """
        获取用户组授权的节点和系统用户，节点下带有资产
        :param user_group:
        :return: {"node": {"assets": "", "system_user": ""}, {}}
        """
        nodes = cls.get_user_group_nodes(user_group)
        nodes_with_assets = dict()
        for node, system_users in nodes.items():
            nodes_with_assets[node] = {
                'assets': node.get_active_assets(),
                'system_users': system_users
            }
        return nodes_with_assets

    @classmethod
    def get_user_group_assets(cls, user_group):
        assets = collections.defaultdict(set)
        permissions = cls.get_user_group_permissions(user_group)

        for perm in permissions:
            for asset in perm.node.get_all_assets():
                assets[asset].add(perm.system_user)
        return assets

    @classmethod
    def get_user_nodes(cls, user):
        nodes = collections.defaultdict(set)
        groups = user.groups.all()
        for group in groups:
            group_nodes = cls.get_user_group_nodes(group)
            for node, system_users in group_nodes.items():
                nodes[node].update(system_users)
        return nodes

    @classmethod
    def get_user_nodes_with_assets(cls, user):
        nodes = cls.get_user_nodes(user)
        nodes_with_assets = dict()
        for node, system_users in nodes.items():
            nodes_with_assets[node] = {
                'assets': node.get_active_assets(),
                'system_users': system_users
            }
        return nodes_with_assets

    @classmethod
    def get_user_assets(cls, user):
        assets = collections.defaultdict(set)
        nodes_with_assets = cls.get_user_nodes_with_assets(user)

        for v in nodes_with_assets.values():
            for asset in v['assets']:
                assets[asset].update(v['system_users'])
        return assets

    @classmethod
    def get_system_user_assets(cls, system_user):
        assets = set()
        permissions = cls.get_system_user_permissions(system_user)

        for perm in permissions:
            assets.update(perm.node.get_all_assets())
        return assets

