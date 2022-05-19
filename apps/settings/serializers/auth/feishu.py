from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.drf.fields import EncryptedField

__all__ = ['FeiShuSettingSerializer']


class FeiShuSettingSerializer(serializers.Serializer):
    FEISHU_APP_ID = serializers.CharField(max_length=256, required=True, label='App ID')
    FEISHU_APP_SECRET = EncryptedField(max_length=256, required=False, label='App Secret')
    AUTH_FEISHU = serializers.BooleanField(default=False, label=_('Enable FeiShu Auth'))

