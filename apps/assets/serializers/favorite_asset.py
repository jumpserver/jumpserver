# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from common.serializers import BulkSerializerMixin
from ..models import FavoriteAsset

__all__ = ['FavoriteAssetSerializer']


class FavoriteAssetSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = FavoriteAsset
        fields = ['user', 'asset']
