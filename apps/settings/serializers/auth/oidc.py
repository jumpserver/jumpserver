from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField

__all__ = [
    'OIDCSettingSerializer', 'KeycloakSettingSerializer',
]


class CommonSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('OIDC')
    # OpenID 公有配置参数 (version <= 1.5.8 或 version >= 1.5.8)
    BASE_SITE_URL = serializers.CharField(
        required=False, allow_null=True, allow_blank=True,
        max_length=1024, label=_('Base site URL'), 
        help_text=_("The current site's URL is used to construct the callback address")
    )
    AUTH_OPENID_CLIENT_ID = serializers.CharField(
        required=False, max_length=1024, label=_('Client Id')
    )
    AUTH_OPENID_CLIENT_SECRET = EncryptedField(
        required=False, max_length=1024, label=_('Client Secret')
    )
    AUTH_OPENID_CLIENT_AUTH_METHOD = serializers.ChoiceField(
        default='client_secret_basic',
        choices=(
            ('client_secret_basic', 'Client Secret Basic'),
            ('client_secret_post', 'Client Secret Post')
        ),
        label=_('Request method')
    )
    AUTH_OPENID_SHARE_SESSION = serializers.BooleanField(required=False, label=_('Share session'))
    AUTH_OPENID_IGNORE_SSL_VERIFICATION = serializers.BooleanField(
        required=False, label=_('Ignore SSL verification')
    )
    AUTH_OPENID_USER_ATTR_MAP = serializers.JSONField(
        required=True, label=_('User attribute'),
        help_text=_(
            "User attribute mapping, where the `key` is the JumpServer user attribute name "
            "and the `value` is the OIDC service user attribute name"
        )
    )
    AUTH_OPENID_PKCE = serializers.BooleanField(required=False, label=_('Enable PKCE'))
    AUTH_OPENID_CODE_CHALLENGE_METHOD = serializers.ChoiceField(
        default='S256', label=_('Code challenge method'),
        choices=(('S256', 'HS256'), ('plain', 'Plain'))
    )


class KeycloakSettingSerializer(CommonSettingSerializer):
    # OpenID 旧配置参数 (version <= 1.5.8 (discarded))
    AUTH_OPENID_KEYCLOAK = serializers.BooleanField(
        label=_("Use Keycloak"), required=False, default=False,
        help_text=_(
            "Use Keycloak as the OpenID Connect server, or use standard OpenID Connect Protocol"
        )
    )
    AUTH_OPENID_SERVER_URL = serializers.CharField(
        required=False, max_length=1024, label=_('Server')
    )
    AUTH_OPENID_REALM_NAME = serializers.CharField(
        required=False, max_length=1024, allow_null=True, label=_('Realm name')
    )


class OIDCSettingSerializer(KeycloakSettingSerializer):
    # OpenID 新配置参数 (version >= 1.5.9)
    AUTH_OPENID = serializers.BooleanField(
        required=False, label=_('OIDC'), help_text=_('OpenID Connect')
    )
    AUTH_OPENID_PROVIDER_ENDPOINT = serializers.CharField(
        required=False, max_length=1024, label=_('Provider endpoint')
    )
    AUTH_OPENID_PROVIDER_AUTHORIZATION_ENDPOINT = serializers.CharField(
        required=False, max_length=1024, label=_('Authorization endpoint')
    )
    AUTH_OPENID_PROVIDER_TOKEN_ENDPOINT = serializers.CharField(
        required=False, max_length=1024, label=_('Token endpoint')
    )
    AUTH_OPENID_PROVIDER_JWKS_ENDPOINT = serializers.CharField(
        required=False, max_length=1024, label=_('JWKS endpoint')
    )
    AUTH_OPENID_PROVIDER_USERINFO_ENDPOINT = serializers.CharField(
        required=False, max_length=1024, label=_('Userinfo endpoint')
    )
    AUTH_OPENID_PROVIDER_END_SESSION_ENDPOINT = serializers.CharField(
        required=False, max_length=1024, label=_('End session endpoint')
    )
    AUTH_OPENID_PROVIDER_SIGNATURE_ALG = serializers.CharField(
        required=False, max_length=1024, label=_('Signature algorithm')
    )
    AUTH_OPENID_PROVIDER_SIGNATURE_KEY = serializers.CharField(
        required=False, max_length=1024, allow_null=True, label=_('Signing key')
    )
    AUTH_OPENID_SCOPES = serializers.CharField(
        required=False, max_length=1024, label=_('Scopes')
    )
    AUTH_OPENID_ID_TOKEN_MAX_AGE = serializers.IntegerField(
        required=False, label=_('ID Token max age (s)')
    )
    AUTH_OPENID_ID_TOKEN_INCLUDE_CLAIMS = serializers.BooleanField(
        required=False, label=_('ID Token include claims')
    )
    AUTH_OPENID_USE_STATE = serializers.BooleanField(
        required=False, label=_('Use state')
    )
    AUTH_OPENID_USE_NONCE = serializers.BooleanField(
        required=False, label=_('Use nonce')
        )
    AUTH_OPENID_ALWAYS_UPDATE_USER = serializers.BooleanField(
        required=False, label=_('Always update user')
    )
