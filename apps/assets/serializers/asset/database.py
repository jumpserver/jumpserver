from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.models import Database, Platform
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_db_name_required()

    def get_platform(self):
        platform = None
        platform_id = None

        if getattr(self, 'initial_data', None):
            platform_id = self.initial_data.get('platform')
            if isinstance(platform_id, dict):
                platform_id = platform_id.get('id') or platform_id.get('pk')
            if not platform_id and self.instance:
                platform = self.instance.platform
        elif getattr(self, 'instance', None):
            if isinstance(self.instance, (list, QuerySet)):
                return
            platform = self.instance.platform
        elif self.context.get('request'):
            platform_id = self.context['request'].query_params.get('platform')

        if not platform and platform_id:
            platform = Platform.objects.filter(id=platform_id).first()
        return platform

    def set_db_name_required(self):
        db_field = self.fields.get('db_name')
        if not db_field:
            return

        platform = self.get_platform()
        if not platform:
            return

        if platform.type in ['mysql', 'mariadb']:
            db_field.required = False
            db_field.allow_blank = True
            db_field.allow_null = True


class DatabaseWithGatewaySerializer(DatabaseSerializer):
    gateway = GatewayWithAccountSecretSerializer()

    class Meta(DatabaseSerializer.Meta):
        fields = DatabaseSerializer.Meta.fields + ['gateway']
