from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField

__all__ = ['FeiShuSettingSerializer']


class FeiShuSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('FeiShu')

    VERSION_CHOICES = (
        ('feishu', _('FeiShu')),
        ('lark', 'Lark')
    )
    AUTH_FEISHU = serializers.BooleanField(default=False, label=_('Enable FeiShu Auth'))
    FEISHU_APP_ID = serializers.CharField(max_length=256, required=True, label='App ID')
    FEISHU_APP_SECRET = EncryptedField(max_length=256, required=False, label='App Secret')
    FEISHU_VERSION = serializers.ChoiceField(
        choices=VERSION_CHOICES, default='feishu', label=_('Version')
    )
