# -*- coding: utf-8 -*-
#

from django.db.models import Q
from rest_framework.views import Response
from django.shortcuts import get_object_or_404

from common.permissions import IsOrgAdmin
from orgs.mixins.api import OrgModelViewSet
from orgs.mixins import generics
from common.utils import get_object_or_none
from ..models import AssetPermission
from ..hands import (
    User, UserGroup, Asset, Node, SystemUser,
)
from .. import serializers


__all__ = [
    'AssetPermissionViewSet', 'AssetPermissionRemoveUserApi',
    'AssetPermissionAddUserApi', 'AssetPermissionRemoveAssetApi',
    'AssetPermissionAddAssetApi', 'AssetPermissionAssetsApi',
]


class AssetPermissionViewSet(OrgModelViewSet):
    """
    资产授权列表的增删改查api
    """
    model = AssetPermission
    serializer_class = serializers.AssetPermissionCreateUpdateSerializer
    filter_fields = ['name']
    permission_classes = (IsOrgAdmin,)

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            "nodes", "assets", "users", "user_groups", "system_users"
        )
        return queryset

    def get_serializer_class(self):
        if self.action in ("list", 'retrieve') and \
                self.request.query_params.get("display"):
            return serializers.AssetPermissionListSerializer
        return self.serializer_class

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

        nodes = set()
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
        query_group = self.request.query_params.get('all')
        if user_id:
            user = get_object_or_none(User, pk=user_id)
        elif username:
            user = get_object_or_none(User, username=username)
        else:
            return queryset
        if not user:
            return queryset.none()
        kwargs = {}
        args = []
        if query_group:
            groups = user.groups.all()
            args.append(Q(users=user) | Q(user_groups__in=groups))
        else:
            kwargs["users"] = user
        return queryset.filter(*args, **kwargs).distinct()

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


class AssetPermissionRemoveUserApi(generics.RetrieveUpdateAPIView):
    """
    将用户从授权中移除，Detail页面会调用
    """
    model = AssetPermission
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateUserSerializer

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            users = serializer.validated_data.get('users')
            if users:
                perm.users.remove(*tuple(users))
                perm.save()
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionAddUserApi(generics.RetrieveUpdateAPIView):
    model = AssetPermission
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateUserSerializer

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            users = serializer.validated_data.get('users')
            if users:
                perm.users.add(*tuple(users))
                perm.save()
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionRemoveAssetApi(generics.RetrieveUpdateAPIView):
    """
    将用户从授权中移除，Detail页面会调用
    """
    model = AssetPermission
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateAssetSerializer

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data.get('assets')
            if assets:
                perm.assets.remove(*tuple(assets))
                perm.save()
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionAddAssetApi(generics.RetrieveUpdateAPIView):
    model = AssetPermission
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateAssetSerializer

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data.get('assets')
            if assets:
                perm.assets.add(*tuple(assets))
                perm.save()
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionAssetsApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionAssetsSerializer
    filter_fields = ("hostname", "ip")
    search_fields = filter_fields

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(AssetPermission, pk=pk)

    def get_queryset(self):
        perm = self.get_object()
        assets = perm.get_all_assets().only(
            *self.serializer_class.Meta.only_fields
        )
        return assets
