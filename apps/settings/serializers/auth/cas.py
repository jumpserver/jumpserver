from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = [
    'CASSettingSerializer',
]


class CASSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('CAS')

    AUTH_CAS = serializers.BooleanField(required=False, label=_('Enable CAS Auth'))
    CAS_SERVER_URL = serializers.CharField(required=False, max_length=1024, label=_('Server url'))
    CAS_ROOT_PROXIED_AS = serializers.CharField(
        required=False, allow_null=True, allow_blank=True,
        max_length=1024, label=_('Proxy server url')
    )
    CAS_LOGOUT_COMPLETELY = serializers.BooleanField(required=False, label=_('Logout completely'))
    CAS_VERSION = serializers.IntegerField(
        required=False, label=_('Version'), min_value=1, max_value=3
    )
    CAS_USERNAME_ATTRIBUTE = serializers.CharField(
        required=False, max_length=1024, label=_('Username attr')
    )
    CAS_APPLY_ATTRIBUTES_TO_USER = serializers.BooleanField(
        required=False, label=_('Enable attributes map')
    )
    CAS_RENAME_ATTRIBUTES = serializers.JSONField(required=False, label=_('Rename attr'))
    CAS_CREATE_USER = serializers.BooleanField(required=False, label=_('Create user if not'))
