# -*- coding: utf-8 -*-
#
from rest_framework_bulk.generics import BulkModelViewSet
from rest_framework.response import Response
from rest_framework import status

from common.permissions import IsValidUser
from orgs.utils import tmp_to_root_org
from ..models import FavoriteAsset, FavoriteFolder
from ..serializers import FavoriteAssetSerializer, FavoriteFolderSerializer

__all__ = ['FavoriteAssetViewSet', 'FavoriteFolderViewSet']


class FavoriteFolderViewSet(BulkModelViewSet):
    serializer_class = FavoriteFolderSerializer
    permission_classes = (IsValidUser,)
    page_no_limit = True

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_root_org():
            return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return FavoriteFolder.objects.filter(user=self.request.user)


class FavoriteAssetViewSet(BulkModelViewSet):
    serializer_class = FavoriteAssetSerializer
    permission_classes = (IsValidUser,)
    filterset_fields = ['asset', 'folder']
    page_no_limit = True

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_root_org():
            return super().dispatch(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        asset_id = request.data.get('asset')
        instance = FavoriteAsset.objects.filter(user=request.user, asset_id=asset_id).first()

        if instance:
            serializer = self.get_serializer(instance, data=request.data, partial=True)
        else:
            serializer = self.get_serializer(data=request.data)
        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = FavoriteAsset.objects.filter(
            user=self.request.user
        ).select_related('asset', 'asset__platform')
        return queryset

    def allow_bulk_destroy(self, qs, filtered):
        return filtered.count() == 1
