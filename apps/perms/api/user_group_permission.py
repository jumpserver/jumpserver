# -*- coding: utf-8 -*-
#
from itertools import chain

from django.db.models import Q
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from common.permissions import IsOrgAdminOrAppUser
from common.utils import lazyproperty
from perms.models import AssetPermission
from assets.models import Asset, Node
from . import user_permission as uapi
from perms import serializers
from perms.utils.asset_permission import get_asset_system_users_id_with_actions_by_group
from assets.api.mixin import SerializeToTreeNodeMixin
from users.models import UserGroup

__all__ = [
    'UserGroupGrantedAssetsApi', 'UserGroupGrantedNodesApi',
    'UserGroupGrantedNodeAssetsApi',
    'UserGroupGrantedNodeChildrenAsTreeApi',
    'UserGroupGrantedAssetSystemUsersApi',
]


class UserGroupMixin:
    @lazyproperty
    def group(self):
        group_id = self.kwargs.get('pk')
        return UserGroup.objects.get(id=group_id)


class UserGroupGrantedAssetsApi(ListAPIView):
    """
    获取用户组直接授权的资产
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')

        return Asset.objects.filter(
            Q(granted_by_permissions__user_groups__id=user_group_id)
        ).distinct().only(
            *self.only_fields
        )


class UserGroupGrantedNodeAssetsApi(ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        node_id = self.kwargs.get("node_id")
        node = Node.objects.get(id=node_id)

        granted = AssetPermission.objects.filter(
            user_groups__id=user_group_id,
            nodes__id=node_id
        ).exists()
        if granted:
            assets = Asset.objects.filter(
                Q(nodes__key__startswith=f'{node.key}:') |
                Q(nodes__key=node.key)
            )
            return assets
        else:
            granted_node_keys = Node.objects.filter(
                granted_by_permissions__user_groups__id=user_group_id,
                key__startswith=f'{node.key}:'
            ).distinct().values_list('key', flat=True)

            granted_node_q = Q()
            for _key in granted_node_keys:
                granted_node_q |= Q(nodes__key__startswith=f'{_key}:')
                granted_node_q |= Q(nodes__key=_key)

            granted_asset_q = (
                Q(granted_by_permissions__user_groups__id=user_group_id) &
                (
                    Q(nodes__key__startswith=f'{node.key}:') |
                    Q(nodes__key=node.key)
                )
            )

            assets = Asset.objects.filter(
                granted_node_q | granted_asset_q
            ).distinct()
            return assets


class UserGroupGrantedNodesApi(ListAPIView):
    serializer_class = serializers.NodeGrantedSerializer
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        nodes = Node.objects.filter(
            Q(granted_by_permissions__user_groups__id=user_group_id) |
            Q(assets__granted_by_permissions__user_groups__id=user_group_id)
        )
        return nodes


class UserGroupGrantedNodeChildrenAsTreeApi(SerializeToTreeNodeMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_children_nodes(self, parent_key):
        return Node.objects.filter(parent_key=parent_key)

    def add_children_key(self, node_key, key, key_set):
        if key.startswith(f'{node_key}:'):
            try:
                end = key.index(':', len(node_key) + 1)
                key_set.add(key[:end])
            except ValueError:
                key_set.add(key)

    def get_nodes(self):
        group_id = self.kwargs.get('pk')
        node_key = self.request.query_params.get('key', None)

        granted_keys = Node.objects.filter(
            granted_by_permissions__user_groups__id=group_id
        ).values_list('key', flat=True)

        asset_granted_keys = Node.objects.filter(
            assets__granted_by_permissions__user_groups__id=group_id
        ).values_list('key', flat=True)

        if node_key is None:
            root_keys = set()
            for _key in chain(granted_keys, asset_granted_keys):
                root_keys.add(_key.split(':', 1)[0])
            return Node.objects.filter(key__in=root_keys)
        else:
            children_keys = set()
            for _key in granted_keys:
                # 判断当前节点是否是授权节点
                if node_key == _key:
                    return self.get_children_nodes(node_key)
                # 判断当前节点有没有授权的父节点
                if node_key.startswith(f'{_key}:'):
                    return self.get_children_nodes(node_key)
                self.add_children_key(node_key, _key, children_keys)

            for _key in asset_granted_keys:
                self.add_children_key(node_key, _key, children_keys)

            return Node.objects.filter(key__in=children_keys)

    def list(self, request, *args, **kwargs):
        nodes = self.get_nodes()
        nodes = self.serialize_nodes(nodes)
        return Response(data=nodes)


class UserGroupGrantedAssetSystemUsersApi(UserGroupMixin, uapi.UserGrantedAssetSystemUsersForAdminApi):
    def get_asset_system_users_id_with_actions(self, asset):
        return get_asset_system_users_id_with_actions_by_group(self.group, asset)
