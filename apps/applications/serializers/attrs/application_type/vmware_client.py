from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from ..application_category import RemoteAppSerializer


__all__ = ['VMwareClientSerializer']


class VMwareClientSerializer(RemoteAppSerializer):
    PATH = r'''
    C:\Program Files (x86)\VMware\Infrastructure\Virtual Infrastructure Client\Launcher\VpxClient
    .exe
    '''
    VMWARE_CLIENT_PATH = ''.join(PATH.split())

    path = serializers.CharField(
        max_length=128, label=_('Application path'), default=VMWARE_CLIENT_PATH,
        allow_null=True
    )
    vmware_target = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Target URL'),
        allow_null=True
    )
    vmware_username = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Username'),
        allow_null=True
    )
    vmware_password = serializers.CharField(
        max_length=128, allow_blank=True, required=False, write_only=True, label=_('Password'),
        allow_null=True
    )
