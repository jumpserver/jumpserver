from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = [
    'AuthSettingSerializer',
]


class AuthSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Authentication')

    AUTH_LDAP = serializers.BooleanField(required=False, label=_('LDAP Auth'))
    AUTH_CAS = serializers.BooleanField(required=False, label=_('CAS Auth'))
    AUTH_OPENID = serializers.BooleanField(required=False, label=_('OPENID Auth'))
    AUTH_SAML2 = serializers.BooleanField(default=False, label=_("SAML2 Auth"))
    AUTH_OAUTH2 = serializers.BooleanField(default=False, label=_("OAuth2 Auth"))
    AUTH_RADIUS = serializers.BooleanField(required=False, label=_('RADIUS Auth'))
    AUTH_DINGTALK = serializers.BooleanField(default=False, label=_('DingTalk Auth'))
    AUTH_FEISHU = serializers.BooleanField(default=False, label=_('FeiShu Auth'))
    AUTH_WECOM = serializers.BooleanField(default=False, label=_('Slack Auth'))
    AUTH_SLACK = serializers.BooleanField(default=False, label=_('WeCom Auth'))
    AUTH_SSO = serializers.BooleanField(default=False, label=_("SSO Auth"))
    AUTH_PASSKEY = serializers.BooleanField(default=False, label=_("Passkey Auth"))
    FORGOT_PASSWORD_URL = serializers.CharField(
        required=False, allow_blank=True, max_length=1024,
        label=_("Forgot password url")
    )
    LOGIN_REDIRECT_MSG_ENABLED = serializers.BooleanField(
        required=False, label=_("Enable login redirect msg")
    )
