# -*- coding: utf-8 -*-
#

from rest_framework.response import Response
from rest_framework import viewsets, status, generics
from rest_framework.pagination import LimitOffsetPagination
from rest_framework import filters
from rest_framework_bulk import BulkModelViewSet
from django.shortcuts import get_object_or_404

from common.permissions import IsOrgAdminOrAppUser, NeedMFAVerify
from common.utils import get_object_or_none, get_logger
from common.mixins import IDInCacheFilterMixin
from ..backends import AssetUserManager
from ..models import Asset, Node, SystemUser, AdminUser
from .. import serializers
from ..tasks import test_asset_users_connectivity_manual


__all__ = [
    'AssetUserViewSet', 'AssetUserAuthInfoApi', 'AssetUserTestConnectiveApi',
    'AssetUserExportViewSet',
]


logger = get_logger(__name__)


class AssetUserFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        kwargs = {}
        for field in view.filter_fields:
            value = request.GET.get(field)
            if not value:
                continue
            if field in ("node_id", "system_user_id", "admin_user_id"):
                continue
            kwargs[field] = value
        return queryset.filter(**kwargs)


class AssetUserSearchBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        value = request.GET.get('search')
        if not value:
            return queryset
        _queryset = AssetUserManager.none()
        for field in view.search_fields:
            if field in ("node_id", "system_user_id", "admin_user_id"):
                continue
            _queryset |= queryset.filter(**{field: value})
        return _queryset


class AssetUserViewSet(IDInCacheFilterMixin, BulkModelViewSet):
    pagination_class = LimitOffsetPagination
    serializer_class = serializers.AssetUserSerializer
    permission_classes = [IsOrgAdminOrAppUser]
    http_method_names = ['get', 'post']
    filter_fields = [
        "id", "ip", "hostname", "username", "asset_id", "node_id",
        "system_user_id", "admin_user_id"
    ]
    search_fields = filter_fields
    filter_backends = (
        filters.OrderingFilter,
        AssetUserFilterBackend, AssetUserSearchBackend,
    )

    def get_queryset(self):
        # 尽可能先返回更少的数据
        username = self.request.GET.get('username')
        asset_id = self.request.GET.get('asset_id')
        node_id = self.request.GET.get('node_id')
        admin_user_id = self.request.GET.get("admin_user_id")
        system_user_id = self.request.GET.get("system_user_id")

        kwargs = {}
        assets = None

        manager = AssetUserManager()
        if system_user_id:
            system_user = get_object_or_404(SystemUser, id=system_user_id)
            assets = system_user.assets.all()
            username = system_user.username
        elif admin_user_id:
            admin_user = get_object_or_404(AdminUser, id=admin_user_id)
            assets = admin_user.assets.all()
            username = admin_user.username
            manager.prefer('admin_user')

        if asset_id:
            asset = get_object_or_404(Asset, id=asset_id)
            assets = [asset]
        elif node_id:
            node = get_object_or_404(Node, id=node_id)
            assets = node.get_all_assets()

        if username:
            kwargs['username'] = username
        if assets is not None:
            kwargs['assets'] = assets

        queryset = manager.filter(**kwargs)
        return queryset


class AssetUserExportViewSet(AssetUserViewSet):
    serializer_class = serializers.AssetUserExportSerializer
    http_method_names = ['get']
    permission_classes = [IsOrgAdminOrAppUser, NeedMFAVerify]


class AssetUserAuthInfoApi(generics.RetrieveAPIView):
    serializer_class = serializers.AssetUserAuthInfoSerializer
    permission_classes = [IsOrgAdminOrAppUser, NeedMFAVerify]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        status_code = status.HTTP_200_OK
        if not instance:
            status_code = status.HTTP_400_BAD_REQUEST
        return Response(serializer.data, status=status_code)

    def get_object(self):
        query_params = self.request.query_params
        username = query_params.get('username')
        asset_id = query_params.get('asset_id')
        prefer = query_params.get("prefer")
        asset = get_object_or_none(Asset, pk=asset_id)
        try:
            manger = AssetUserManager()
            instance = manger.get(username, asset, prefer=prefer)
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        else:
            return instance


class AssetUserTestConnectiveApi(generics.RetrieveAPIView):
    """
    Test asset users connective
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.TaskIDSerializer

    def get_asset_users(self):
        username = self.request.GET.get('username')
        asset_id = self.request.GET.get('asset_id')
        prefer = self.request.GET.get("prefer")
        asset = get_object_or_none(Asset, pk=asset_id)
        manager = AssetUserManager()
        asset_users = manager.filter(username=username, assets=[asset], prefer=prefer)
        return asset_users

    def retrieve(self, request, *args, **kwargs):
        asset_users = self.get_asset_users()
        prefer = self.request.GET.get("prefer")
        kwargs = {}
        if prefer == "admin_user":
            kwargs["run_as_admin"] = True
        task = test_asset_users_connectivity_manual.delay(asset_users, **kwargs)
        return Response({"task": task.id})


class AssetUserPushApi(generics.CreateAPIView):
    """
    Test asset users connective
    """
    serializer_class = serializers.AssetUserPushSerializer
    permission_classes = (IsOrgAdminOrAppUser,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset = serializer.validated_data["asset"]
        username = serializer.validated_data["username"]
        pass
