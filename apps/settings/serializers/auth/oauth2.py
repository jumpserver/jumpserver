from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from common.utils import static_or_direct

__all__ = [
    'OAuth2SettingSerializer',
]


class SettingImageField(serializers.ImageField):
    def to_representation(self, value):
        return static_or_direct(value)


class OAuth2SettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('OAuth2')

    AUTH_OAUTH2 = serializers.BooleanField(
        default=False, label=_('Enable OAuth2 Auth')
    )
    AUTH_OAUTH2_LOGO_PATH = SettingImageField(
        allow_null=True, required=False, label=_('Logo')
    )
    AUTH_OAUTH2_PROVIDER = serializers.CharField(
        required=True, max_length=16, label=_('Service provider')
    )
    AUTH_OAUTH2_CLIENT_ID = serializers.CharField(
        required=True, max_length=1024, label=_('Client Id')
    )
    AUTH_OAUTH2_CLIENT_SECRET = EncryptedField(
        required=False, max_length=1024, label=_('Client Secret')
    )
    AUTH_OAUTH2_SCOPE = serializers.CharField(
        required=True, max_length=1024, label=_('Scope'), allow_blank=True
    )
    AUTH_OAUTH2_PROVIDER_AUTHORIZATION_ENDPOINT = serializers.CharField(
        required=True, max_length=1024, label=_('Provider auth endpoint')
    )
    AUTH_OAUTH2_ACCESS_TOKEN_ENDPOINT = serializers.CharField(
        required=True, max_length=1024, label=_('Provider token endpoint')
    )
    AUTH_OAUTH2_ACCESS_TOKEN_METHOD = serializers.ChoiceField(
        default='GET', label=_('Client authentication method'),
        choices=(('GET', 'GET'), ('POST', 'POST-DATA'), ('POST_JSON', 'POST-JSON'))
    )
    AUTH_OAUTH2_PROVIDER_USERINFO_ENDPOINT = serializers.CharField(
        required=True, max_length=1024, label=_('Provider userinfo endpoint')
    )
    AUTH_OAUTH2_PROVIDER_END_SESSION_ENDPOINT = serializers.CharField(
        required=False, allow_blank=True, max_length=1024, label=_('Provider end session endpoint')
    )
    AUTH_OAUTH2_LOGOUT_COMPLETELY = serializers.BooleanField(required=False, label=_('Logout completely'))
    AUTH_OAUTH2_USER_ATTR_MAP = serializers.JSONField(
        required=True, label=_('User attr map')
    )
    AUTH_OAUTH2_ALWAYS_UPDATE_USER = serializers.BooleanField(
        default=True, label=_('Always update user')
    )
