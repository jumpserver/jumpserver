# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from common.serializers import BulkSerializerMixin
from ..models import FavoriteAsset, FavoriteFolder

__all__ = ['FavoriteAssetSerializer', 'FavoriteFolderSerializer']


class FavoriteFolderSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = FavoriteFolder
        fields = ['id', 'user', 'name', 'parent', 'date_created']
        read_only_fields = ['id', 'date_created']


class FavoriteAssetSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    asset_info = serializers.SerializerMethodField()

    class Meta:
        model = FavoriteAsset
        fields = ['user', 'asset', 'folder', 'asset_info']

    @staticmethod
    def _get_icon(asset, platform):
        from assets.const import AllTypes
        support_types = AllTypes.get_types_values(exclude_custom=True)
        if asset.category == 'device':
            return 'switch'
        if asset.type in support_types:
            return asset.type
        return 'file'

    def get_asset_info(self, obj):
        asset = obj.asset
        platform = asset.platform
        return {
            'id': str(asset.id),
            'name': asset.name,
            'iconSkin': self._get_icon(asset, platform),
            'chkDisabled': not asset.is_active,
            'meta': {
                'type': 'asset',
                'data': {
                    'platform_type': platform.type,
                    'org_name': asset.org_name,
                    'name': asset.name,
                    'address': asset.address,
                },
            },
        }
