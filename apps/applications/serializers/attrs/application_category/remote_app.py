# coding: utf-8
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist

from common.utils import get_logger, is_uuid
from assets.models import Asset

logger = get_logger(__file__)


__all__ = ['RemoteAppSerializer']


class CharPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):

    def to_internal_value(self, data):
        instance = super().to_internal_value(data)
        return str(instance.id)

    def to_representation(self, value):
        # value is instance.id
        if self.pk_field is not None:
            return self.pk_field.to_representation(value)
        return value


class RemoteAppSerializer(serializers.Serializer):
    asset_info = serializers.SerializerMethodField()
    asset = CharPrimaryKeyRelatedField(
        queryset=Asset.objects, required=False, label=_("Asset"), allow_null=True
    )
    path = serializers.CharField(
        max_length=128, label=_('Application path'), allow_null=True
    )

    @staticmethod
    def get_asset_info(obj):
        asset_id = obj.get('asset')
        if not asset_id or is_uuid(asset_id):
            return {}
        try:
            asset = Asset.objects.filter(id=str(asset_id)).values_list('id', 'hostname')
        except ObjectDoesNotExist as e:
            logger.error(e)
            return {}
        if not asset:
            return {}
        asset_info = {'id': str(asset[0]), 'hostname': asset[1]}
        return asset_info
