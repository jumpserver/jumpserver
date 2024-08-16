from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from common.utils import static_or_direct
from .base import OrgListField

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
            'User attribute mapping, where the `key` is the JumpServer user attribute name and the '
            '`value` is the OAuth2 service user attribute name'
        )
    )
    AUTH_OAUTH2_ALWAYS_UPDATE_USER = serializers.BooleanField(
        default=True, label=_('Always update user')
    )
    OAUTH2_ORG_IDS = OrgListField()
