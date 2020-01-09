# -*- coding: utf-8 -*-
#

from django.http import Http404
from django.conf import settings
from rest_framework.response import Response
from rest_framework import generics, filters
from rest_framework_bulk import BulkModelViewSet

from common.permissions import IsOrgAdminOrAppUser, NeedMFAVerify
from common.utils import get_object_or_none, get_logger
from common.mixins import CommonApiMixin
from ..backends import AssetUserManager
from ..models import Asset, Node
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
            if field == "node_id":
                value = get_object_or_none(Node, pk=value)
                kwargs["node"] = value
                continue
            elif field == "asset_id":
                field = "asset"
            elif field in ["system_user_id", "admin_user_id"]:
                field = "prefer_id"
            kwargs[field] = value
        if kwargs:
            queryset = queryset.filter(**kwargs)
        logger.debug("Filter {}".format(kwargs))
        return queryset


class AssetUserSearchBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        value = request.GET.get('search')
        if not value:
            return queryset
        queryset = queryset.search(value)
        return queryset


class AssetUserViewSet(CommonApiMixin, BulkModelViewSet):
    serializer_classes = {
        'default': serializers.AssetUserWriteSerializer,
        'list': serializers.AssetUserReadSerializer,
        'retrieve': serializers.AssetUserReadSerializer,
    }
    permission_classes = [IsOrgAdminOrAppUser]
    http_method_names = ['get', 'post']
    filter_fields = [
        "ip", "hostname", "username",
        "asset_id", "node_id",
        "system_user_id", "admin_user_id"
    ]
    search_fields = ["ip", "hostname", "username"]
    filter_backends = [
        AssetUserFilterBackend, AssetUserSearchBackend,
    ]

    def allow_bulk_destroy(self, qs, filtered):
        return False

    def get_queryset(self):
        manager = AssetUserManager()
        queryset = manager.all()
        return queryset


class AssetUserExportViewSet(AssetUserViewSet):
    serializer_classes = {"default": serializers.AssetUserExportSerializer}
    http_method_names = ['get']
    permission_classes = [IsOrgAdminOrAppUser]

    def get_permissions(self):
        if settings.SECURITY_VIEW_AUTH_NEED_MFA:
            self.permission_classes = [IsOrgAdminOrAppUser, NeedMFAVerify]
        return super().get_permissions()


class AssetUserAuthInfoApi(generics.RetrieveAPIView):
    serializer_class = serializers.AssetUserAuthInfoSerializer
    permission_classes = [IsOrgAdminOrAppUser]

    def get_permissions(self):
        if settings.SECURITY_VIEW_AUTH_NEED_MFA:
            self.permission_classes = [IsOrgAdminOrAppUser, NeedMFAVerify]
        return super().get_permissions()

    def get_object(self):
        query_params = self.request.query_params
        username = query_params.get('username')
        asset_id = query_params.get('asset_id')
        prefer_id = query_params.get("prefer_id")
        asset = get_object_or_none(Asset, pk=asset_id)
        try:
            manger = AssetUserManager()
            instance = manger.get_object(username=username, asset=asset, prefer_id=prefer_id)
        except Exception as e:
            print("Error: ", e)
            raise Http404("Not found")
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
        prefer_id = self.request.GET.get("prefer_id")
        asset = get_object_or_none(Asset, pk=asset_id)
        manager = AssetUserManager()
        asset_users = manager.filter(
            username=username, assets=[asset],
            prefer_id=prefer_id
        )
        return asset_users

    def retrieve(self, request, *args, **kwargs):
        asset_users = self.get_asset_users()
        prefer = self.request.GET.get("prefer")
        kwargs = {}
        if prefer == "admin_user":
            kwargs["run_as_admin"] = True
        asset_users = list(asset_users)
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
