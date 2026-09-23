from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from common.utils import static_or_direct
from .base import OrgListField
from ..tls import CertificateVerifyMode, validate_ca_certificate

__all__ = [
    'OAuth2SettingSerializer',
]


class SettingImageField(serializers.ImageField):
    def to_representation(self, value):
        return static_or_direct(value)


class OAuth2SettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('OAuth2')

    AUTH_OAUTH2 = serializers.BooleanField(
        default=False, label=_('OAuth2')
    )
    AUTH_OAUTH2_LOGO_PATH = SettingImageField(
        allow_null=True, required=False, label=_('Logo')
    )
    AUTH_OAUTH2_PROVIDER = serializers.CharField(
        required=True, max_length=16, label=_('Service provider')
    )
    AUTH_OAUTH2_CLIENT_ID = serializers.CharField(
        required=True, max_length=1024, label=_('Client ID')
    )
    AUTH_OAUTH2_CLIENT_SECRET = EncryptedField(
        required=False, max_length=1024, label=_('Client Secret')
    )
    AUTH_OAUTH2_SCOPE = serializers.CharField(
        required=True, max_length=1024, label=_('Scope'), allow_blank=True
    )
    AUTH_OAUTH2_PROVIDER_AUTHORIZATION_ENDPOINT = serializers.CharField(
        required=True, max_length=1024, label=_('Authorization endpoint')
    )
    AUTH_OAUTH2_ACCESS_TOKEN_ENDPOINT = serializers.CharField(
        required=True, max_length=1024, label=_('Token endpoint')
    )
    AUTH_OAUTH2_ACCESS_TOKEN_METHOD = serializers.ChoiceField(
        default='GET', label=_('Request method'),
        choices=(('GET', 'GET'), ('POST', 'POST-DATA'), ('POST_JSON', 'POST-JSON'))
    )
    AUTH_OAUTH2_PROVIDER_USERINFO_ENDPOINT = serializers.CharField(
        required=True, max_length=1024, label=_('Userinfo endpoint')
    )
    AUTH_OAUTH2_CERT_VERIFY_MODE = serializers.ChoiceField(
        choices=CertificateVerifyMode.choices,
        default=CertificateVerifyMode.default,
        label=_('Certificate verification'),
        help_text=_('Controls verification of OAuth2 server TLS certificates')
    )
    AUTH_OAUTH2_CACERT_CONTENT = EncryptedField(
        allow_blank=True, required=False, write_only=True,
        max_length=1024 * 1024,
        label=_('CA certificate'),
        help_text=_('PEM certificate used in addition to the system trust store')
    )
    AUTH_OAUTH2_CACERT_CONFIGURED = serializers.SerializerMethodField(
        method_name='get_ca_configured'
    )
    AUTH_OAUTH2_PROVIDER_END_SESSION_ENDPOINT = serializers.CharField(
        required=False, allow_blank=True, max_length=1024, label=_('End session endpoint')
    )
    AUTH_OAUTH2_LOGOUT_COMPLETELY = serializers.BooleanField(
        required=False, label=_('Logout completely'),
        help_text=_('When the user signs out, they also be logged out from the OAuth2 server')
    )
    AUTH_OAUTH2_USER_ATTR_MAP = serializers.JSONField(
        required=True, label=_('User attribute'),
        help_text=_(
            'User attribute mapping, where the `key` is this system user attribute name and the '
            '`value` is the OAuth2 service user attribute name'
        )
    )
    AUTH_OAUTH2_ALWAYS_UPDATE_USER = serializers.BooleanField(
        default=True, label=_('Always update user')
    )
    OAUTH2_ORG_IDS = OrgListField()

    def get_ca_configured(self, _obj):
        submitted = getattr(self, '_validated_data', {})
        if 'AUTH_OAUTH2_CACERT_CONTENT' in submitted:
            return bool(submitted['AUTH_OAUTH2_CACERT_CONTENT'])
        return bool(settings.AUTH_OAUTH2_CACERT_CONTENT)

    def validate(self, attrs):
        field_name = 'AUTH_OAUTH2_CACERT_CONTENT'
        ca_cert = attrs.get(field_name)
        validate_ca_certificate(ca_cert, field_name)

        verify_mode = attrs.get(
            'AUTH_OAUTH2_CERT_VERIFY_MODE', settings.AUTH_OAUTH2_CERT_VERIFY_MODE
        )
        existing_ca = settings.AUTH_OAUTH2_CACERT_CONTENT
        effective_ca = ca_cert if field_name in attrs else existing_ca
        if verify_mode == CertificateVerifyMode.custom_ca and not effective_ca:
            raise serializers.ValidationError({
                field_name: _('A CA certificate is required')
            })
        return attrs
