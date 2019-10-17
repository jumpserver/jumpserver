# -*- coding: utf-8 -*-
#

from common.permissions import IsValidUser

from rest_framework_bulk import BulkModelViewSet

from ..models import FavoriteAsset
from ..serializers import FavoriteAssetSerializer

__all__ = ['FavoriteAssetViewSet']


class FavoriteAssetViewSet(BulkModelViewSet):
    serializer_class = FavoriteAssetSerializer
    permission_classes = [IsValidUser]
    filterset_fields = ['asset']

    def get_queryset(self):
        return FavoriteAsset.objects.all().filter(user=self.request.user)
