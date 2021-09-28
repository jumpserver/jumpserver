from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = ['WeComSettingSerializer']


class WeComSettingSerializer(serializers.Serializer):
    WECOM_CORPID = serializers.CharField(max_length=256, required=True, label='corpid')
    WECOM_AGENTID = serializers.CharField(max_length=256, required=True, label='agentid')
    WECOM_SECRET = serializers.CharField(max_length=256, required=False, label='secret', write_only=True)
    AUTH_WECOM = serializers.BooleanField(default=False, label=_('Enable WeCom Auth'))