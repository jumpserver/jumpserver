# -*- coding: utf-8 -*-
#
from django.db.models import Q
from django.utils.decorators import method_decorator
from perms.api.user_permission.mixin import UserNodeGrantStatusDispatchMixin
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from django.conf import settings

from assets.api.mixin import SerializeToTreeNodeMixin
from common.utils import get_logger
from ...hands import Node
from ... import serializers
from perms.utils.user_node_tree import (
    get_node_all_granted_assets, get_direct_granted_assets
)
from perms.pagination import GrantedAssetLimitOffsetPagination
from assets.models import Asset
from orgs.utils import tmp_to_root_org
from .mixin import ForAdminMixin, ForUserMixin


logger = get_logger(__name__)

__all__ = [
    'UserDirectGrantedAssetsForAdminApi', 'MyAllAssetsAsTreeApi',
    'UserGrantedNodeAssetsForAdminApi', 'MyDirectGrantedAssetsApi',
    'UserDirectGrantedAssetsAsTreeForAdminApi', 'MyGrantedNodeAssetsApi',
    'MyUngroupAssetsAsTreeApi',
]


@method_decorator(tmp_to_root_org(), name='list')
class UserDirectGrantedAssetsApi(ListAPIView):
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']

    def get_queryset(self):
        user = self.user
        assets = get_direct_granted_assets(user)\
            .prefetch_related('platform').only(*self.only_fields)
        return assets


@method_decorator(tmp_to_root_org(), name='list')
class AssetsAsTreeMixin(SerializeToTreeNodeMixin):
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = self.serialize_assets(queryset, None)
        return Response(data=data)


class UserDirectGrantedAssetsForAdminApi(ForAdminMixin, UserDirectGrantedAssetsApi):
    pass


class MyDirectGrantedAssetsApi(ForUserMixin, UserDirectGrantedAssetsApi):
    pass


@method_decorator(tmp_to_root_org(), name='list')
class UserDirectGrantedAssetsAsTreeForAdminApi(ForAdminMixin, AssetsAsTreeMixin, UserDirectGrantedAssetsApi):
    pass


@method_decorator(tmp_to_root_org(), name='list')
class MyUngroupAssetsAsTreeApi(ForUserMixin, AssetsAsTreeMixin, UserDirectGrantedAssetsApi):
    def get_queryset(self):
        queryset = super().get_queryset()
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            queryset = queryset.none()
        return queryset


@method_decorator(tmp_to_root_org(), name='list')
class UserAllGrantedAssetsApi(ListAPIView):
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields

    def get_queryset(self):
        user = self.user

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


class MyAllAssetsAsTreeApi(ForUserMixin, AssetsAsTreeMixin, UserAllGrantedAssetsApi):
    pass


@method_decorator(tmp_to_root_org(), name='list')
class UserGrantedNodeAssetsApi(UserNodeGrantStatusDispatchMixin, ListAPIView):
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']
    pagination_class = GrantedAssetLimitOffsetPagination

    def get_queryset(self):
        node_id = self.kwargs.get("node_id")
        node = Node.objects.get(id=node_id)
        return self.dispatch_get_data(node.key, self.user)

    def get_data_on_node_direct_granted(self, key):
        # 最初的写法是：
        #   Asset.objects.filter(Q(nodes__key__startswith=f'{node.key}:') | Q(nodes__id=node.id))
        #   可是 startswith 会导致表关联时 Asset 索引失效
        node_ids = Node.objects.filter(
            Q(key__startswith=f'{key}:') |
            Q(key=key)
        ).values_list('id', flat=True).distinct()
        return Asset.objects.filter(nodes__id__in=list(node_ids)).distinct()

    def get_data_on_node_indirect_granted(self, key):
        return get_node_all_granted_assets(self.user, key)

    def get_data_on_node_not_granted(self, key):
        return Asset.objects.none()


class UserGrantedNodeAssetsForAdminApi(ForAdminMixin, UserGrantedNodeAssetsApi):
    pass


class MyGrantedNodeAssetsApi(ForUserMixin, UserGrantedNodeAssetsApi):
    pass
