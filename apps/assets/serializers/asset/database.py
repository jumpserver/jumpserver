from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from assets.models import Database
from assets.serializers.gateway import GatewayWithAccountSecretSerializer
from .common import AssetSerializer

__all__ = ['DatabaseSerializer', 'DatabaseWithGatewaySerializer']


class DatabaseSerializer(AssetSerializer):
    db_name = serializers.CharField(max_length=1024, label=_('Default database'), required=True)

    class Meta(AssetSerializer.Meta):
        model = Database
        extra_fields = [
            'db_name', 'use_ssl', 'ca_cert', 'client_cert',
            'client_key', 'allow_invalid_cert'
        ]
        fields = AssetSerializer.Meta.fields + extra_fields

    def validate(self, attrs):
        platform = attrs.get('platform')
        db_type_required = ('mongodb', 'postgresql')
        if platform and getattr(platform, 'type') in db_type_required \
                and not attrs.get('db_name'):
            raise ValidationError({'db_name': _('This field is required.')})
        return attrs


class DatabaseWithGatewaySerializer(DatabaseSerializer):
    gateway = GatewayWithAccountSecretSerializer()

    class Meta(DatabaseSerializer.Meta):
        fields = DatabaseSerializer.Meta.fields + ['gateway']
