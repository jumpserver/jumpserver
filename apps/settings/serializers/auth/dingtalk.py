from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.drf.fields import EncryptedField

__all__ = ['DingTalkSettingSerializer']


class DingTalkSettingSerializer(serializers.Serializer):
    DINGTALK_AGENTID = serializers.CharField(max_length=256, required=True, label='AgentId')
    DINGTALK_APPKEY = serializers.CharField(max_length=256, required=True, label='AppKey')
    DINGTALK_APPSECRET = EncryptedField(max_length=256, required=False, label='AppSecret')
    AUTH_DINGTALK = serializers.BooleanField(default=False, label=_('Enable DingTalk Auth'))
