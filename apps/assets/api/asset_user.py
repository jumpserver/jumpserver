# -*- coding: utf-8 -*-
#
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
    'AssetUserViewSet', 'AssetUserAuthInfoViewSet', 'AssetUserTaskBaseView',
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
    def filter_queryset(self, request, queryset, view):
        latest = request.GET.get('latest') == '1'
        if latest:
            queryset = queryset.distinct()
        return queryset


class AssetUserViewSet(CommonApiMixin, BulkModelViewSet):
    serializer_classes = {
        'default': serializers.AssetUserWriteSerializer,
        'list': serializers.AssetUserReadSerializer,
        'retrieve': serializers.AssetUserReadSerializer,
    }
    permission_classes = [IsOrgAdminOrAppUser]
    filter_fields = [
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
        queryset = self.get_queryset()
        obj = queryset.get(id=pk)
        return obj
    #
    # def get_exception_handler(self):
    #     def handler(e, context):
    #         return Response({"error": str(e)}, status=400)
    #     return handler

    def perform_destroy(self, instance):
        manager = AssetUserManager()
        manager.delete(instance)

    def get_queryset(self):
        manager = AssetUserManager()
        queryset = manager.all()
        return queryset


class AssetUserAuthInfoViewSet(AssetUserViewSet):
    serializer_classes = {"default": serializers.AssetUserAuthInfoSerializer}
    http_method_names = ['get']
    permission_classes = [IsOrgAdminOrAppUser]

    def get_permissions(self):
        if settings.SECURITY_VIEW_AUTH_NEED_MFA:
            self.permission_classes = [IsOrgAdminOrAppUser, NeedMFAVerify]
        return super().get_permissions()


class AssetUserTaskBaseView(generics.CreateAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetUserTaskSerializer
    filter_backends = AssetUserViewSet.filter_backends
    filter_fields = AssetUserViewSet.filter_fields

    def get_object(self):
        pk = self.kwargs.get('pk')
        manager = AssetUserManager()
        instance = manager.get(id=pk)
        return instance

    @staticmethod
    def test_asset_user_connectivity(asset_user):
        kwargs = {}
        if asset_user.backend == "admin_user":
            kwargs["run_as_admin"] = True
        asset_users = [asset_user]
        task = test_asset_users_connectivity_manual.delay(asset_users, **kwargs)
        return task

    def perform_create(self, serializer):
        asset_user = self.get_object()
        #action = serializer.validated_data["action"]
        #only this
        task = self.test_asset_user_connectivity(asset_user)
        return task

    def get_exception_handler(self):
        def handler(e, context):
            return Response({"error": str(e)}, status=400)
        return handler

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = self.perform_create(serializer)
        return Response({"task": task.id}, status=201)


