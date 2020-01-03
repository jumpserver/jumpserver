# -*- coding: utf-8 -*-
#

from django.db.models import Q

from common.permissions import IsOrgAdmin
from orgs.mixins.api import OrgModelViewSet
from common.utils import get_object_or_none
from ..models import AssetPermission
from ..hands import (
    User, UserGroup, Asset, Node, SystemUser,
)
from .. import serializers


__all__ = [
    'AssetPermissionViewSet',
]


class AssetPermissionViewSet(OrgModelViewSet):
    """
    资产授权列表的增删改查api
    """
    model = AssetPermission
    serializer_classes = {
        'default': serializers.AssetPermissionCreateUpdateSerializer,
        'display': serializers.AssetPermissionListSerializer
    }
    filter_fields = ['name']
    permission_classes = (IsOrgAdmin,)

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            "nodes", "assets", "users", "user_groups", "system_users"
        )
        return queryset

    def is_query_all(self):
        query_all = self.request.query_params.get('all', '1') == '1'
        return query_all

    def filter_valid(self, queryset):
        valid_query = self.request.query_params.get('is_valid', None)
        if valid_query is None:
            return queryset
        invalid = valid_query in ['0', 'N', 'false', 'False']
        if invalid:
            queryset = queryset.invalid()
        else:
            queryset = queryset.valid()
        return queryset

    def filter_system_user(self, queryset):
        system_user_id = self.request.query_params.get('system_user_id')
        system_user_name = self.request.query_params.get('system_user')
        if system_user_id:
            system_user = get_object_or_none(SystemUser, pk=system_user_id)
        elif system_user_name:
            system_user = get_object_or_none(SystemUser, name=system_user_name)
        else:
            return queryset
        if not system_user:
            return queryset.none()
        queryset = queryset.filter(system_users=system_user)
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

    def filter_user(self, queryset):
        user_id = self.request.query_params.get('user_id')
        username = self.request.query_params.get('username')
        if user_id:
            user = get_object_or_none(User, pk=user_id)
        elif username:
            user = get_object_or_none(User, username=username)
        else:
            return queryset
        if not user:
            return queryset.none()
        if not self.is_query_all():
            queryset = queryset.filter(users=user)
            return queryset
        groups = user.groups.all()
        queryset = queryset.filter(
            Q(users=user) | Q(user_groups__in=groups)
        ).distinct()
        return queryset

    def filter_user_group(self, queryset):
        user_group_id = self.request.query_params.get('user_group_id')
        user_group_name = self.request.query_params.get('user_group')
        if user_group_id:
            group = get_object_or_none(UserGroup, pk=user_group_id)
        elif user_group_name:
            group = get_object_or_none(UserGroup, name=user_group_name)
        else:
            return queryset
        if not group:
            return queryset.none()
        queryset = queryset.filter(user_groups=group)
        return queryset

    def filter_keyword(self, queryset):
        keyword = self.request.query_params.get('search')
        if not keyword:
            return queryset
        queryset = queryset.filter(name__icontains=keyword)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_valid(queryset)
        queryset = self.filter_user(queryset)
        queryset = self.filter_keyword(queryset)
        queryset = self.filter_asset(queryset)
        queryset = self.filter_node(queryset)
        queryset = self.filter_system_user(queryset)
        queryset = self.filter_user_group(queryset)
        queryset = queryset.distinct()
        return queryset
