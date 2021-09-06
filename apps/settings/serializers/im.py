from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


class WeComSettingSerializer(serializers.Serializer):
    WECOM_CORPID = serializers.CharField(max_length=256, required=True, label='corpid')
    WECOM_AGENTID = serializers.CharField(max_length=256, required=True, label='agentid')
    WECOM_SECRET = serializers.CharField(max_length=256, required=False, label='secret', write_only=True)
    AUTH_WECOM = serializers.BooleanField(default=False, label=_('Enable WeCom Auth'))


class DingTalkSettingSerializer(serializers.Serializer):
    DINGTALK_AGENTID = serializers.CharField(max_length=256, required=True, label='AgentId')
    DINGTALK_APPKEY = serializers.CharField(max_length=256, required=True, label='AppKey')
    DINGTALK_APPSECRET = serializers.CharField(max_length=256, required=False, label='AppSecret', write_only=True)
    AUTH_DINGTALK = serializers.BooleanField(default=False, label=_('Enable DingTalk Auth'))


class FeiShuSettingSerializer(serializers.Serializer):
    FEISHU_APP_ID = serializers.CharField(max_length=256, required=True, label='App ID')
    FEISHU_APP_SECRET = serializers.CharField(max_length=256, required=False, label='App Secret', write_only=True)
    AUTH_FEISHU = serializers.BooleanField(default=False, label=_('Enable FeiShu Auth'))

