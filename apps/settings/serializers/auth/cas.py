
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = [
    'CASSettingSerializer',
]


class CASSettingSerializer(serializers.Serializer):
    AUTH_CAS = serializers.BooleanField(required=False, label=_('Enable CAS Auth'))
    CAS_SERVER_URL = serializers.CharField(required=False, max_length=1024, label=_('Server url'))
    CAS_LOGOUT_COMPLETELY = serializers.BooleanField(required=False, label=_('Logout completely'))
    CAS_VERSION = serializers.IntegerField(required=False, label=_('Version'))
    CAS_USERNAME_ATTRIBUTE = serializers.CharField(required=False, max_length=1024, label=_('Username attr'))
    CAS_APPLY_ATTRIBUTES_TO_USER = serializers.BooleanField(required=False, label=_('Apply attr to use'))
    CAS_RENAME_ATTRIBUTES = serializers.DictField(required=False, label=_('Rename attr'))
    CAS_CREATE_USER = serializers.BooleanField(required=False, label=_('Create User'))