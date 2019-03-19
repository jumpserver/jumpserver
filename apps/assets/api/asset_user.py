# -*- coding: utf-8 -*-
#


from rest_framework.response import Response
from rest_framework import viewsets, status, generics
from rest_framework.pagination import LimitOffsetPagination

from common.permissions import IsOrgAdminOrAppUser
from common.utils import get_object_or_none, get_logger

from ..backends.multi import AssetUserManager
from ..models import Asset
from .. import serializers
from ..tasks import test_asset_users_connectivity_manual


__all__ = [
    'AssetUserViewSet', 'AssetUserAuthInfoApi', 'AssetUserTestConnectiveApi',
]


logger = get_logger(__name__)


class AssetUserViewSet(viewsets.GenericViewSet):
    pagination_class = LimitOffsetPagination
    serializer_class = serializers.AssetUserSerializer
    permission_classes = (IsOrgAdminOrAppUser, )
    http_method_names = ['get', 'post']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        username = self.request.GET.get('username')
        asset_id = self.request.GET.get('asset_id')
        asset = get_object_or_none(Asset, pk=asset_id)
        queryset = AssetUserManager.filter(username=username, asset=asset)
        return queryset

    def filter_queryset(self, queryset):
        queryset = sorted(
            queryset,
            key=lambda q: (q.asset.hostname, q.connectivity, q.username)
        )
        return queryset


class AssetUserAuthInfoApi(generics.RetrieveAPIView):
    serializer_class = serializers.AssetUserAuthInfoSerializer
    permission_classes = (IsOrgAdminOrAppUser,)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        status_code = status.HTTP_200_OK
        if not instance:
            status_code = status.HTTP_400_BAD_REQUEST
        return Response(serializer.data, status=status_code)

    def get_object(self):
        username = self.request.GET.get('username')
        asset_id = self.request.GET.get('asset_id')
        asset = get_object_or_none(Asset, pk=asset_id)
        try:
            instance = AssetUserManager.get(username, asset)
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
        else:
            return instance


class AssetUserTestConnectiveApi(generics.RetrieveAPIView):
    """
    Test asset users connective
    """

    def get_asset_users(self):
        username = self.request.GET.get('username')
        asset_id = self.request.GET.get('asset_id')
        asset = get_object_or_none(Asset, pk=asset_id)
        asset_users = AssetUserManager.filter(username=username, asset=asset)
        return asset_users

    def retrieve(self, request, *args, **kwargs):
        asset_users = self.get_asset_users()
        task = test_asset_users_connectivity_manual.delay(asset_users)
        return Response({"task": task.id})



