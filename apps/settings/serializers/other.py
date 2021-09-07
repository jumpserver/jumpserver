from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


class OtherSettingSerializer(serializers.Serializer):
    AUTH_SSO = serializers.BooleanField(required=False, label=_('Enable SSO Auth'))
    AUTH_SSO_AUTHKEY_TTL = serializers.IntegerField(required=False, label=_('SSO authkey ttl'))

    OTP_VALID_WINDOW = serializers.IntegerField(required=False, label=_('OTP valid window'))
    OTP_ISSUER_NAME = serializers.CharField(required=False, max_length=1024, label=_('OTP issuer name'))

    PERIOD_TASK_ENABLED = serializers.BooleanField(required=False, label=_("Enable period task"))
    EMAIL_SUFFIX = serializers.CharField(required=False, label=_("Email suffix"))
    PERM_SINGLE_ASSET_TO_UNGROUP_NODE = serializers.BooleanField(required=False, label=_("Perm single to ungroup node"))
    WINDOWS_SSH_DEFAULT_SHELL = serializers.CharField(required=False, label=_('Ansible windows default shell'))

    FORGOT_PASSWORD_URL = serializers.CharField(required=False, label=_("Forgot password url"))
    HEALTH_CHECK_TOKEN = serializers.CharField(required=False, label=_("Health check token"))
    LOGIN_REDIRECT_MSG_ENABLED = serializers.BooleanField(required=False, label=_("Disable login redirect msg"))
