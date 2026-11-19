from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
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
            'client_key', 'allow_invalid_cert', 'pg_ssl_mode'
        ]
        fields = AssetSerializer.Meta.fields + extra_fields
        extra_kwargs = {
            'ca_cert': {'help_text': _('CA cert help text')},
            'pg_ssl_mode': {'help_text': _('Postgresql ssl model help text')},
        }
        extra_kwargs.update(AssetSerializer.Meta.extra_kwargs)

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

        if not platform and platform_id and str(platform_id).isdigit():
            platform = Platform.objects.filter(id=platform_id).first()
        return platform

    def set_db_name_required(self):
        db_field = self.fields.get('db_name')
        if not db_field:
            return

        platform = self.get_platform()
        if not platform:
            return

        if platform.type in [
            'mysql', 'mariadb', 'oracle', 'sqlserver',
            'db2', 'dameng', 'oceanbase', 'clickhouse', 'redis'
        ]:
            db_field.required = False
            db_field.allow_blank = True
            db_field.allow_null = True

    def validate(self, attrs):
        attrs = super().validate(attrs)
        platform = self.get_platform()
        if not platform or platform.type not in ('mysql', 'mariadb', 'postgresql'):
            return attrs
        fields = ('use_ssl', 'ca_cert', 'client_cert', 'client_key', 'allow_invalid_cert', 'pg_ssl_mode')
        if self.instance and not any(field in attrs for field in fields):
            return attrs

        def value(key, default=''):
            return attrs.get(key, getattr(self.instance, key, default))

        if not value('use_ssl', False):
            return attrs
        if platform.type == 'postgresql':
            if 'pg_ssl_mode' not in attrs and not getattr(self.instance, 'use_ssl', False):
                attrs['pg_ssl_mode'] = 'verify-full'
            mode = value('pg_ssl_mode', 'verify-full')
            if mode in ('verify-ca', 'verify-full') and value('allow_invalid_cert', False):
                raise serializers.ValidationError({
                    'allow_invalid_cert': _('Certificate verification cannot be disabled in verify-ca or verify-full mode.')
                })
        cert, key = value('client_cert'), value('client_key')
        if bool(cert) != bool(key):
            missing = 'client_key' if cert else 'client_cert'
            raise serializers.ValidationError({missing: _('Configure the client certificate and private key together.')})
        certificates = {}
        for field in ('ca_cert', 'client_cert'):
            pem = value(field)
            if not pem:
                continue
            try:
                if len(pem) > 1048576 or 'PRIVATE KEY' in pem:
                    raise ValueError
                certificates[field] = x509.load_pem_x509_certificates(pem.encode())
                if not certificates[field]:
                    raise ValueError
            except (ValueError, TypeError, UnsupportedAlgorithm):
                raise serializers.ValidationError({field: _('Upload a valid PEM certificate bundle (maximum 1 MiB).')})
        if key:
            try:
                if len(key) > 65536:
                    raise ValueError
                private_key = serialization.load_pem_private_key(key.encode(), password=None)
                encoding, format = serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
                key_public = private_key.public_key().public_bytes(encoding, format)
                cert_public = certificates['client_cert'][0].public_key().public_bytes(encoding, format)
                if key_public != cert_public:
                    raise ValueError
            except (ValueError, TypeError, UnsupportedAlgorithm):
                raise serializers.ValidationError({
                    'client_key': _('Upload an unencrypted PEM private key matching the client certificate (maximum 64 KiB).')
                })
        return attrs


class DatabaseWithGatewaySerializer(DatabaseSerializer):
    gateway = GatewayWithAccountSecretSerializer()

    class Meta(DatabaseSerializer.Meta):
        fields = DatabaseSerializer.Meta.fields + ['gateway']
