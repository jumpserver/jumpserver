# -*- coding: utf-8 -*-
#
from rest_framework_bulk import BulkModelViewSet

from common.permissions import IsValidUser
from orgs.utils import tmp_to_root_org
from ..models import FavoriteAsset
from ..serializers import FavoriteAssetSerializer

__all__ = ['FavoriteAssetViewSet']


class FavoriteAssetViewSet(BulkModelViewSet):
    serializer_class = FavoriteAssetSerializer
    permission_classes = (IsValidUser,)
    filterset_fields = ['asset']

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_root_org():
            return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = FavoriteAsset.objects.filter(user=self.request.user)
        return queryset

    def allow_bulk_destroy(self, qs, filtered):
        return filtered.count() == 1
