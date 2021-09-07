from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = ['FeiShuSettingSerializer']


class FeiShuSettingSerializer(serializers.Serializer):
    FEISHU_APP_ID = serializers.CharField(max_length=256, required=True, label='App ID')
    FEISHU_APP_SECRET = serializers.CharField(max_length=256, required=False, label='App Secret', write_only=True)
    AUTH_FEISHU = serializers.BooleanField(default=False, label=_('Enable FeiShu Auth'))

