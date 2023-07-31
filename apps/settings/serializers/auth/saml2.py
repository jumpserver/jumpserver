from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = [
    'SAML2SettingSerializer',
]


class SAML2SettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('SAML2')

    AUTH_SAML2 = serializers.BooleanField(
        default=False, required=False, label=_('Enable SAML2 Auth')
    )
    SAML2_IDP_METADATA_URL = serializers.URLField(
        allow_blank=True, required=False, label=_('IDP metadata URL')
    )
    SAML2_IDP_METADATA_XML = serializers.CharField(
        allow_blank=True, required=False, label=_('IDP metadata XML')
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
    SAML2_RENAME_ATTRIBUTES = serializers.JSONField(required=False, label=_('Rename attr'))
    SAML2_LOGOUT_COMPLETELY = serializers.BooleanField(required=False, label=_('Logout completely'))
    AUTH_SAML2_ALWAYS_UPDATE_USER = serializers.BooleanField(required=False, label=_('Always update user'))
