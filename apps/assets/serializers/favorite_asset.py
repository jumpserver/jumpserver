# -*- coding: utf-8 -*-
#

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers import BulkSerializerMixin
from ..models import FavoriteAsset, FavoriteFolder

__all__ = [
    'FavoriteAssetSerializer', 'FavoriteAssetsToFolderSerializer',
    'FavoriteFolderSerializer',
]


class FavoriteFolderSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=FavoriteFolder.objects.all(), allow_null=True, required=False
    )
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = FavoriteFolder
        fields = ['id', 'user', 'name', 'parent', 'date_created']
        read_only_fields = ['id', 'date_created']
        validators = []

    def validate_parent(self, parent):
        if parent is None:
            return parent
        user = self.context['request'].user
        if parent.user_id != user.id:
            raise serializers.ValidationError(_('Invalid favorite folder.'))
        instance = self.instance
        current = parent
        while instance and current:
            if current.id == instance.id:
                raise serializers.ValidationError(_('A folder cannot be moved below itself.'))
            current = current.parent
        return parent

    def validate(self, attrs):
        user = self.context['request'].user
        parent = attrs.get('parent', getattr(self.instance, 'parent', None))
        if parent is None:
            return attrs

        name = attrs.get('name', getattr(self.instance, 'name', ''))
        duplicates = FavoriteFolder.objects.filter(
            user=user, parent=parent, name__iexact=name
        )
        if self.instance:
            duplicates = duplicates.exclude(id=self.instance.id)
        if duplicates.exists():
            raise serializers.ValidationError({
                'name': _('A folder with this name already exists under the parent folder.')
            })
        return attrs


class FavoriteAssetSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    folder = serializers.PrimaryKeyRelatedField(
        queryset=FavoriteFolder.objects.all(), allow_null=True, required=False
    )
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    asset_info = serializers.SerializerMethodField()

    class Meta:
        model = FavoriteAsset
        fields = ['user', 'asset', 'folder', 'asset_info']

    def validate(self, attrs):
        request = self.context['request']
        user = request.user
        folder = attrs.get('folder', getattr(self.instance, 'folder', None))
        if folder is not None and folder.user_id != user.id:
            raise serializers.ValidationError({
                'folder': _('Invalid favorite folder.')
            })
        asset = attrs.get('asset', getattr(self.instance, 'asset', None))
        if asset is not None:
            from orgs.utils import tmp_to_org
            from perms.utils import UserPermAssetUtil

            with tmp_to_org(asset.org_id):
                permitted = (
                    UserPermAssetUtil(user).get_all_assets()
                    .filter(id=asset.id).exists()
                )
            if not permitted:
                raise serializers.ValidationError({
                    'asset': _('Asset is not authorized for this user.')
                })
        return attrs

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


class FavoriteAssetsToFolderSerializer(serializers.Serializer):
    assets = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False
    )
    folder = serializers.PrimaryKeyRelatedField(
        queryset=FavoriteFolder.objects.all(), allow_null=True,
        required=False, default=None,
    )

    def validate_assets(self, assets):
        # Preserve the user's selection order while avoiding duplicate work.
        return list(dict.fromkeys(assets))

    def validate_folder(self, folder):
        if folder is None:
            return folder
        request = self.context.get('request')
        if request is None or folder.user_id != request.user.id:
            raise serializers.ValidationError(_('Invalid favorite folder.'))
        return folder
