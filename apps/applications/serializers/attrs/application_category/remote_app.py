# coding: utf-8
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist

from common.utils import get_logger, is_uuid, get_object_or_none
from assets.models import Asset

logger = get_logger(__file__)

__all__ = ['RemoteAppSerializer']


class ExistAssetPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):

    def to_internal_value(self, data):
        instance = super().to_internal_value(data)
        return str(instance.id)

    def to_representation(self, _id):
        # _id 是 instance.id
        if self.pk_field is not None:
            return self.pk_field.to_representation(_id)
        # 解决删除资产后，远程应用更新页面会显示资产ID的问题
        asset = get_object_or_none(Asset, id=_id)
        if not asset:
            return None
        return _id


class RemoteAppSerializer(serializers.Serializer):
    asset_info = serializers.SerializerMethodField()
    asset = ExistAssetPrimaryKeyRelatedField(
        queryset=Asset.objects, required=True, label=_("Asset"), allow_null=True
    )
    path = serializers.CharField(
        max_length=128, label=_('Application path'), allow_null=True
    )

    def validate_asset(self, asset):
        if not asset:
            raise serializers.ValidationError(_('This field is required.'))
        return asset

    @staticmethod
    def get_asset_info(obj):
        asset_id = obj.get('asset')
        if not asset_id or not is_uuid(asset_id):
            return {}
        try:
            asset = Asset.objects.get(id=str(asset_id))
        except ObjectDoesNotExist as e:
            logger.error(e)
            return {}
        if not asset:
            return {}
        asset_info = {'id': str(asset.id), 'hostname': asset.hostname}
        return asset_info
