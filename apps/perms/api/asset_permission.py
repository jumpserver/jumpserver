# -*- coding: utf-8 -*-
#

from django.utils import timezone
from django.db.models import Q
from rest_framework.views import Response
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework import viewsets
from rest_framework.pagination import LimitOffsetPagination

from common.permissions import IsOrgAdmin
from common.utils import get_object_or_none
from ..models import AssetPermission, Action
from ..hands import (
    User, UserGroup, Asset, Node, SystemUser,
)
from .. import serializers


__all__ = [
    'AssetPermissionViewSet', 'AssetPermissionRemoveUserApi',
    'AssetPermissionAddUserApi', 'AssetPermissionRemoveAssetApi',
    'AssetPermissionAddAssetApi', 'ActionViewSet',
]


class ActionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Action.objects.all()
    serializer_class = serializers.ActionSerializer
    permission_classes = (IsOrgAdmin,)


class AssetPermissionViewSet(viewsets.ModelViewSet):
    """
    资产授权列表的增删改查api
    """
    queryset = AssetPermission.objects.all()
    serializer_class = serializers.AssetPermissionCreateUpdateSerializer
    pagination_class = LimitOffsetPagination
    filter_fields = ['name']
    permission_classes = (IsOrgAdmin,)

    def get_serializer_class(self):
        if self.action in ("list", 'retrieve'):
            return serializers.AssetPermissionListSerializer
        return self.serializer_class

    def filter_valid(self, queryset):
        valid = self.request.query_params.get('is_valid', None)
        if valid is None:
            return queryset
        if valid in ['0', 'N', 'false', 'False']:
            valid = False
        else:
            valid = True
        now = timezone.now()
        if valid:
            queryset = queryset.filter(is_active=True).filter(
                date_start__lt=now, date_expired__gt=now,
            )
        else:
            queryset = queryset.filter(
                Q(is_active=False) |
                Q(date_start__gt=now) |
                Q(date_expired__lt=now)
            )
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
            node = get_object_or_none(Node, pk=node_id)
        elif node_name:
            node = get_object_or_none(Node, name=node_name)
        else:
            return queryset
        if not node:
            return queryset.none()
        nodes = node.get_ancestor(with_self=True)
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
        inherit_nodes = set()
        for asset in assets:
            for node in asset.nodes.all():
                inherit_nodes.update(set(node.get_ancestor(with_self=True)))
        queryset = queryset.filter(Q(assets__in=assets) | Q(nodes__in=inherit_nodes))
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
        queryset = self.filter_keyword(queryset)
        queryset = self.filter_asset(queryset)
        queryset = self.filter_node(queryset)
        queryset = self.filter_system_user(queryset)
        queryset = self.filter_user_group(queryset)
        return queryset

    def get_queryset(self):
        return self.queryset.all()


class AssetPermissionRemoveUserApi(RetrieveUpdateAPIView):
    """
    将用户从授权中移除，Detail页面会调用
    """
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateUserSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            users = serializer.validated_data.get('users')
            if users:
                perm.users.remove(*tuple(users))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionAddUserApi(RetrieveUpdateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateUserSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            users = serializer.validated_data.get('users')
            if users:
                perm.users.add(*tuple(users))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionRemoveAssetApi(RetrieveUpdateAPIView):
    """
    将用户从授权中移除，Detail页面会调用
    """
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateAssetSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data.get('assets')
            if assets:
                perm.assets.remove(*tuple(assets))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionAddAssetApi(RetrieveUpdateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateAssetSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data.get('assets')
            if assets:
                perm.assets.add(*tuple(assets))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})
