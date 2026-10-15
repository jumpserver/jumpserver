from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from .base import OrgListField
from ..tls import CertificateVerifyMode, validate_ca_certificate

__all__ = [
    'SAML2SettingSerializer',
]


class SAML2SettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('SAML2')

    AUTH_SAML2 = serializers.BooleanField(
        default=False, required=False, label=_('SAML2')
    )
    SAML2_IDP_METADATA_URL = serializers.URLField(
        allow_blank=True, required=False, label=_('IDP Metadata URL')
    )
    SAML2_IDP_METADATA_XML = serializers.CharField(
        allow_blank=True, required=False, label=_('IDP Metadata XML')
    )
    SAML2_IDP_METADATA_CERT_VERIFY_MODE = serializers.ChoiceField(
        choices=CertificateVerifyMode.choices,
        default=CertificateVerifyMode.system,
        label=_('Certificate verification'),
        help_text=_('Controls verification when downloading IDP Metadata')
    )
    SAML2_IDP_METADATA_CACERT_CONTENT = EncryptedField(
        allow_blank=True, required=False, write_only=True,
        max_length=1024 * 1024,
        label=_('CA certificate'),
        help_text=_('PEM certificate used in addition to the system trust store')
    )
    SAML2_IDP_METADATA_CACERT_CONFIGURED = serializers.SerializerMethodField(
        method_name='get_ca_configured'
    )
    SAML2_SP_ADVANCED_SETTINGS = serializers.JSONField(
        required=False, label=_('SP advanced settings')
    )
    SAML2_SP_KEY_CONTENT = serializers.CharField(
        allow_blank=True, required=False,
        write_only=True, label=_('SP private key')
    )
    SAML2_SP_CERT_CONTENT = serializers.CharField(
        allow_blank=True, required=False,
        write_only=True, label=_('SP cert')
    )
    SAML2_RENAME_ATTRIBUTES = serializers.JSONField(
        required=False, label=_('User attribute'),
        help_text=_(
            "User attribute mapping, where the `key` is the SAML2 service user attribute name "
            "and the `value` is this system user attribute name"
        )
    )
    SAML2_LOGOUT_COMPLETELY = serializers.BooleanField(
        required=False, label=_('Logout completely'),
        help_text=_('When the user signs out, they also be logged out from the SAML2 server')
    )
    AUTH_SAML2_ALWAYS_UPDATE_USER = serializers.BooleanField(required=False, label=_('Always update user'))
    SAML2_ORG_IDS = OrgListField()

    def get_ca_configured(self, _obj):
        submitted = getattr(self, '_validated_data', {})
        submitted_ca = submitted.get('SAML2_IDP_METADATA_CACERT_CONTENT')
        return bool(submitted_ca or settings.SAML2_IDP_METADATA_CACERT_CONTENT)

    def validate(self, attrs):
        field_name = 'SAML2_IDP_METADATA_CACERT_CONTENT'
        ca_cert = attrs.get(field_name)
        validate_ca_certificate(ca_cert, field_name)

        metadata_url = attrs.get(
            'SAML2_IDP_METADATA_URL', settings.SAML2_IDP_METADATA_URL
        )
        verify_mode = attrs.get(
            'SAML2_IDP_METADATA_CERT_VERIFY_MODE',
            settings.SAML2_IDP_METADATA_CERT_VERIFY_MODE,
        )
        effective_ca = ca_cert or settings.SAML2_IDP_METADATA_CACERT_CONTENT
        if (
            metadata_url
            and verify_mode == CertificateVerifyMode.custom_ca
            and not effective_ca
        ):
            raise serializers.ValidationError({
                field_name: _('A CA certificate is required')
            })
        return attrs
