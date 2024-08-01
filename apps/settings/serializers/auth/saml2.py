from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .base import OrgListField

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
            "and the `value` is the JumpServer user attribute name"
        )
    )
    SAML2_LOGOUT_COMPLETELY = serializers.BooleanField(
        required=False, label=_('Logout completely'),
        help_text=_('When the user signs out, they also be logged out from the SAML2 server')
    )
    AUTH_SAML2_ALWAYS_UPDATE_USER = serializers.BooleanField(required=False, label=_('Always update user'))
    SAML2_ORG_IDS = OrgListField()
