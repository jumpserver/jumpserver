# -*- coding: utf-8 -*-
#
import coreapi
from django.conf import settings
from rest_framework.response import Response
from rest_framework import generics, filters
from rest_framework_bulk import BulkModelViewSet

from common.permissions import IsOrgAdminOrAppUser, NeedMFAVerify
from common.utils import get_object_or_none, get_logger
from common.mixins import CommonApiMixin
from ..backends import AssetUserManager
from ..models import Asset, Node, SystemUser
from .. import serializers
from ..tasks import (
    test_asset_users_connectivity_manual, push_system_user_a_asset_manual
)


__all__ = [
    'AssetUserViewSet', 'AssetUserAuthInfoViewSet', 'AssetUserTaskCreateAPI',
]


logger = get_logger(__name__)


class AssetUserFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        kwargs = {}
        for field in view.filterset_fields:
            value = request.GET.get(field)
            if not value:
                continue
            if field == "node_id":
                value = get_object_or_none(Node, pk=value)
                kwargs["node"] = value
                continue
            elif field == "asset_id":
                field = "asset"
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


class AssetUserLatestFilterBackend(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='latest', location='query', required=False,
                type='string', example='1',
                description='Only the latest version'
            )
        ]

    def filter_queryset(self, request, queryset, view):
        latest = request.GET.get('latest') == '1'
        if latest:
            queryset = queryset.distinct()
        return queryset


class AssetUserViewSet(CommonApiMixin, BulkModelViewSet):
    serializer_classes = {
        'default': serializers.AssetUserWriteSerializer,
        'display': serializers.AssetUserReadSerializer,
        'retrieve': serializers.AssetUserReadSerializer,
    }
    permission_classes = [IsOrgAdminOrAppUser]
    filterset_fields = [
        "id", "ip", "hostname", "username",
        "asset_id", "node_id",
        "prefer", "prefer_id",
    ]
    search_fields = ["ip", "hostname", "username"]
    filter_backends = [
        AssetUserFilterBackend, AssetUserSearchBackend,
        AssetUserLatestFilterBackend,
    ]

    def allow_bulk_destroy(self, qs, filtered):
        return False

    def get_object(self):
        pk = self.kwargs.get("pk")
        if pk is None:
            return
        queryset = self.get_queryset()
        obj = queryset.get(id=pk)
        return obj

    def get_exception_handler(self):
        def handler(e, context):
            logger.error(e, exc_info=True)
            return Response({"error": str(e)}, status=400)
        return handler

    def perform_destroy(self, instance):
        manager = AssetUserManager()
        manager.delete(instance)

    def get_queryset(self):
        manager = AssetUserManager()
        queryset = manager.all()
        return queryset


class AssetUserAuthInfoViewSet(AssetUserViewSet):
    serializer_classes = {"default": serializers.AssetUserAuthInfoSerializer}
    http_method_names = ['get', 'post']
    permission_classes = [IsOrgAdminOrAppUser]

    def get_permissions(self):
        if settings.SECURITY_VIEW_AUTH_NEED_MFA:
            self.permission_classes = [IsOrgAdminOrAppUser, NeedMFAVerify]
        return super().get_permissions()


class AssetUserTaskCreateAPI(generics.CreateAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetUserTaskSerializer
    filter_backends = AssetUserViewSet.filter_backends
    filterset_fields = AssetUserViewSet.filterset_fields

    def get_asset_users(self):
        manager = AssetUserManager()
        queryset = manager.all()
        for cls in self.filter_backends:
            queryset = cls().filter_queryset(self.request, queryset, self)
        return list(queryset)

    def perform_create(self, serializer):
        asset_users = self.get_asset_users()
        # action = serializer.validated_data["action"]
        # only this
        # if action == "test":
        task = test_asset_users_connectivity_manual.delay(asset_users)
        data = getattr(serializer, '_data', {})
        data["task"] = task.id
        setattr(serializer, '_data', data)
        return task

    def get_exception_handler(self):
        def handler(e, context):
            return Response({"error": str(e)}, status=400)
        return handler
