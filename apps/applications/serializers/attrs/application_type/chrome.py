from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from ..application_category import RemoteAppSerializer


__all__ = ['ChromeSerializer']


class ChromeSerializer(RemoteAppSerializer):
    CHROME_PATH = 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'

    path = serializers.CharField(
        max_length=128, label=_('Application path'), default=CHROME_PATH
    )
    chrome_target = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Target URL')
    )
    chrome_username = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Username')
    )
    chrome_password = serializers.CharField(
        max_length=128, allow_blank=True, required=False, write_only=True, label=_('Password')
    )

