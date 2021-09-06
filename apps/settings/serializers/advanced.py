from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


class AdvancedSettingSerializer(serializers.Serializer):



    AUTH_SSO = serializers.BooleanField(required=False, label=_('Enable SSO Auth'))
    AUTH_SSO_AUTHKEY_TTL = serializers.IntegerField(required=False, label=_('SSO authkey ttl'))
    OTP_VALID_WINDOW = serializers.IntegerField(required=False, label=_('OTP valid window'))
    OTP_ISSUER_NAME = serializers.CharField(required=False, max_length=1024, label=_('OTP issuer name'))
    SECURITY_LOGIN_CHALLENGE_ENABLED = serializers.BooleanField(required=False, label=_('Login challenge enabled'))
    SECURITY_LOGIN_CAPTCHA_ENABLED = serializers.BooleanField(required=False, label=_('Login captcha enabled'))
    SECURITY_INSECURE_COMMAND_LEVEL = serializers.IntegerField(required=False, label=_('Insecure command level'))