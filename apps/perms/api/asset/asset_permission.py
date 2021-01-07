# -*- coding: utf-8 -*-
#
from django.db.models import Q

from perms.models import AssetPermission
from perms.hands import (
    Asset, Node
)
from perms import serializers
from ..base import BasePermissionViewSet


__all__ = [
    'AssetPermissionViewSet',
]


class AssetPermissionViewSet(BasePermissionViewSet):
    """
    资产授权列表的增删改查api
    """
    model = AssetPermission
    serializer_class = serializers.AssetPermissionSerializer
    filterset_fields = ['name']
    custom_filter_fields = BasePermissionViewSet.custom_filter_fields + [
        'node_id', 'node', 'asset_id', 'hostname', 'ip'
    ]

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            "nodes", "assets", "users", "user_groups", "system_users"
        )
        return queryset

    def filter_node(self, queryset):
        node_id = self.request.query_params.get('node_id')
        node_name = self.request.query_params.get('node')
        if node_id:
            _nodes = Node.objects.filter(pk=node_id)
        elif node_name:
            _nodes = Node.objects.filter(value=node_name)
        else:
            return queryset
        if not _nodes:
            return queryset.none()

        if not self.is_query_all():
            queryset = queryset.filter(nodes__in=_nodes)
            return queryset
        nodes = set(_nodes)
        for node in _nodes:
            nodes |= set(node.get_ancestors(with_self=True))
        queryset = queryset.filter(nodes__in=nodes)
        return queryset

    def filter_asset(self, queryset):
        asset_id = self.request.query_params.get('asset_id')
        hostname = self.request.query_params.get('hostname')
        ip = self.request.query_params.get('ip')
        if asset_id:
            assets = Asset.objects.filter(pk=asset_id)
        elif hostname:
            assets = Asset.objects.filter(hostname=hostname)
        elif ip:
            assets = Asset.objects.filter(ip=ip)
        else:
            return queryset
        if not assets:
            return queryset.none()
        if not self.is_query_all():
            queryset = queryset.filter(assets__in=assets)
            return queryset
        inherit_all_nodes = set()
        inherit_nodes_keys = assets.all().values_list('nodes__key', flat=True)

        for key in inherit_nodes_keys:
            if key is None:
                continue
            ancestor_keys = Node.get_node_ancestor_keys(key, with_self=True)
            inherit_all_nodes.update(ancestor_keys)
        queryset = queryset.filter(
            Q(assets__in=assets) | Q(nodes__key__in=inherit_all_nodes)
        ).distinct()
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_asset(queryset)
        queryset = self.filter_node(queryset)
        return queryset
