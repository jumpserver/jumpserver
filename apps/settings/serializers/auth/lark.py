from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField

__all__ = ['LarkSettingSerializer']


class LarkSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = 'Lark'

    AUTH_LARK = serializers.BooleanField(default=False, label=_('Enable Lark Auth'))
    LARK_APP_ID = serializers.CharField(max_length=256, required=True, label='App ID')
    LARK_APP_SECRET = EncryptedField(max_length=256, required=False, label='App Secret')
