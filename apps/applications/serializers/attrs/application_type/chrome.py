from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.drf.fields import EncryptedField
from ..application_category import RemoteAppSerializer

__all__ = ['ChromeSerializer', 'ChromeSecretSerializer']


class ChromeSerializer(RemoteAppSerializer):
    CHROME_PATH = 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'

    path = serializers.CharField(
        max_length=128, label=_('Application path'), default=CHROME_PATH, allow_null=True,
    )
    chrome_target = serializers.CharField(
        max_length=128, allow_blank=True, required=False,
        label=_('Target URL'), allow_null=True,
    )
    chrome_username = serializers.CharField(
        max_length=128, allow_blank=True, required=False,
        label=_('Chrome username'), allow_null=True,
    )
    chrome_password = EncryptedField(
        max_length=128, allow_blank=True, required=False,
        label=_('Chrome password'), allow_null=True
    )


class ChromeSecretSerializer(ChromeSerializer):
    chrome_password = EncryptedField(
        max_length=128, allow_blank=True, required=False,
        label=_('Chrome password'), allow_null=True, write_only=False
    )
