# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from orgs.utils import tmp_to_root_org
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
