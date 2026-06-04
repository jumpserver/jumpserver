from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from common.serializers.fields import EncryptedField
from django.conf import settings
from django.db.models import TextChoices

__all__ = ['UKeySettingSerializer']


class UKeySettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('UKey')

    AUTH_UKEY = serializers.BooleanField(
        default=False, label=_('UKey')
    )
    AUTH_UKEY_CHALLENGE_TTL = serializers.IntegerField(
        default=300, label=_('Challenge TTL (seconds)'),
        help_text=_('Time-to-live (seconds) for authentication challenge codes')
    )
    AUTH_UKEY_DEFAULT_PIN = EncryptedField(
        default='', allow_blank=True, label=_('USB-Key Default PIN'),
        help_text=_('Default USB Key PIN used for administrator reset')
    )
    # ENROLLMENT SETTINGS
    AUTH_UKEY_ENROLL_ENABLED = serializers.BooleanField(
        default=False, label=_('Enrollment'),
        help_text=_('Whether to enable user certificate enrollment')
    )
    AUTH_UKEY_ENROLL_VALIDITY_DAYS = serializers.IntegerField(
        default=365, label=_('Enrollment Validity Days'), min_value=1,
        help_text=_('Validity period (days) for issued certificates')
    )
    AUTH_UKEY_CA_KEY_CONTENT = EncryptedField(
        default='', allow_blank=True, label=_('CA Key'),
        help_text=_('PEM content of CA private key used for certificate enrollment')
    )
    AUTH_UKEY_CA_CERT_CONTENT = EncryptedField(
        default='', allow_blank=True, label=_('CA Cert'),
        help_text=_('PEM content of CA certificate used for certificate enrollment and authentication')
    )
    AUTH_UKEY_CA_KEY_PASS = EncryptedField(
        default='', allow_blank=True, label=_('CA Key Password'),
        help_text=_('Password for CA private key used for certificate enrollment (leave blank if not set)')
    )
    AUTH_UKEY_CA_CERT_ALGORITHM = serializers.SerializerMethodField(
        label=_('CA Cert Algorithm')
    )

    def get_AUTH_UKEY_CA_CERT_ALGORITHM(self, obj):
        from authentication.backends.ukey.sdk import ukey_sdk_config
        algo = ukey_sdk_config.ca_cert_asym_alg
        return algo or _('Auto-Detect After Upload')
