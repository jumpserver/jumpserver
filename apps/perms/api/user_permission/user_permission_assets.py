# -*- coding: utf-8 -*-
#
from django.db.models import Q
from django.utils.decorators import method_decorator
from perms.api.user_permission.mixin import UserGrantedNodeDispatchMixin
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from assets.api.mixin import SerializeToTreeNodeMixin
from common.utils import get_object_or_none
from users.models import User
from common.permissions import IsOrgAdminOrAppUser, IsValidUser
from common.utils import get_logger
from ...hands import Node
from ... import serializers
from perms.models import UserGrantedMappingNode
from perms.utils.user_node_tree import get_node_all_granted_assets
from perms.pagination import GrantedAssetLimitOffsetPagination
from assets.models import Asset
from orgs.utils import tmp_to_root_org


logger = get_logger(__name__)

__all__ = [
    'UserGrantedAssetsForAdminApi', 'MyGrantedAssetsAsTreeApi',
    'UserGrantedNodeAssetsForAdminApi', 'MyGrantedAssetsApi',
    'UserGrantedAssetsAsTreeForAdminApi', 'MyGrantedNodeAssetsApi',
    'MyUngroupAssetsAsTreeApi',
]


class UserGrantedAssetsForAdminApi(ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']

    def get_user(self):
        return User.objects.get(id=self.kwargs.get('pk'))

    def get_queryset(self):
        user = self.get_user()

        return Asset.objects.filter(
            Q(granted_by_permissions__users=user) |
            Q(granted_by_permissions__user_groups__users=user)
        ).distinct().only(
            *self.only_fields
        )


@method_decorator(tmp_to_root_org(), name='list')
class MyGrantedAssetsApi(UserGrantedAssetsForAdminApi):
    permission_classes = (IsValidUser,)

    def get_user(self):
        return self.request.user


@method_decorator(tmp_to_root_org(), name='list')
class UserGrantedAssetsAsTreeForAdminApi(SerializeToTreeNodeMixin, UserGrantedAssetsForAdminApi):
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = self.serialize_assets(queryset, None)
        return Response(data=data)


@method_decorator(tmp_to_root_org(), name='list')
class MyUngroupAssetsAsTreeApi(UserGrantedAssetsAsTreeForAdminApi):
    """
    获取 直接授权 的资产
    """
    permission_classes = (IsValidUser,)

    def get_user(self):
        return self.request.user


@method_decorator(tmp_to_root_org(), name='list')
class MyGrantedAssetsAsTreeApi(UserGrantedAssetsAsTreeForAdminApi):
    """
    获取 直接授权 + 节点授权 的资产
    """
    permission_classes = (IsValidUser, )

    def get_queryset(self):
        user = self.get_user()

        granted_node_keys = Node.objects.filter(
            Q(granted_by_permissions__users=user) |
            Q(granted_by_permissions__user_groups__users=user)
        ).distinct().values_list('key', flat=True)

        granted_node_q = Q()
        for _key in granted_node_keys:
            granted_node_q |= Q(nodes__key__startswith=f'{_key}:')
            granted_node_q |= Q(nodes__key=_key)

        q = Q(granted_by_permissions__users=user) | \
            Q(granted_by_permissions__user_groups__users=user)

        if granted_node_q:
            q |= granted_node_q

        return Asset.objects.filter(q).distinct().only(
            *self.only_fields
        )

    def get_user(self):
        return self.request.user


@method_decorator(tmp_to_root_org(), name='list')
class UserGrantedNodeAssetsForAdminApi(UserGrantedNodeDispatchMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']
    pagination_class = GrantedAssetLimitOffsetPagination

    def get_user(self):
        return User.objects.get(id=self.kwargs.get('pk'))

    def get_queryset(self):
        node_id = self.kwargs.get("node_id")
        user = self.get_user()

        mapping_node: UserGrantedMappingNode = get_object_or_none(
            UserGrantedMappingNode, user=user, node_id=node_id)
        node = Node.objects.get(id=node_id)
        return self.dispatch_node_process(node.key, mapping_node, node)

    def on_granted_node(self, key, mapping_node: UserGrantedMappingNode, node: Node = None):
        self.node = node
        return Asset.objects.filter(
            Q(nodes__key__startswith=f'{node.key}:') |
            Q(nodes__id=node.id)
        ).distinct()

    def on_ungranted_node(self, key, mapping_node: UserGrantedMappingNode, node: Node = None):
        self.node = mapping_node
        user = self.get_user()
        return get_node_all_granted_assets(user, node.key)


@method_decorator(tmp_to_root_org(), name='list')
class MyGrantedNodeAssetsApi(UserGrantedNodeAssetsForAdminApi):
    permission_classes = (IsValidUser,)

    def get_user(self):
        return self.request.user
