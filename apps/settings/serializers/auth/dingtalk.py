from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = ['DingTalkSettingSerializer']


class DingTalkSettingSerializer(serializers.Serializer):
    DINGTALK_AGENTID = serializers.CharField(max_length=256, required=True, label='AgentId')
    DINGTALK_APPKEY = serializers.CharField(max_length=256, required=True, label='AppKey')
    DINGTALK_APPSECRET = serializers.CharField(max_length=256, required=False, label='AppSecret', write_only=True)
    AUTH_DINGTALK = serializers.BooleanField(default=False, label=_('Enable DingTalk Auth'))
