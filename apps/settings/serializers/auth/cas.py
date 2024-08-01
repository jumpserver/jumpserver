from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .base import OrgListField

__all__ = [
    'CASSettingSerializer',
]


class CASSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('CAS')

    AUTH_CAS = serializers.BooleanField(required=False, label=_('CAS'))
    CAS_SERVER_URL = serializers.CharField(required=False, max_length=1024, label=_('Server'))
    CAS_ROOT_PROXIED_AS = serializers.CharField(
        required=False, allow_null=True, allow_blank=True,
        max_length=1024, label=_('Proxy Server')
    )
    CAS_LOGOUT_COMPLETELY = serializers.BooleanField(
        required=False, label=_('Logout completely'),
        help_text=_('When the user signs out, they also be logged out from the CAS server')
    )
    CAS_VERSION = serializers.IntegerField(
        required=False, label=_('Version'), min_value=1, max_value=3
    )
    CAS_USERNAME_ATTRIBUTE = serializers.CharField(
        required=False, max_length=1024, label=_('Username attr')
    )
    CAS_APPLY_ATTRIBUTES_TO_USER = serializers.BooleanField(
        required=False, label=_('Enable attributes map')
    )
    CAS_RENAME_ATTRIBUTES = serializers.JSONField(
        required=False, label=_('User attribute'),
        help_text=_(
            "User attribute mapping, where the `key` is the CAS service user attribute name "
            "and the `value` is the JumpServer user attribute name"
        )
    )
    CAS_CREATE_USER = serializers.BooleanField(
        required=False, label=_('Create user'),
        help_text=_(
            'After successful user authentication, if the user does not exist, '
            'automatically create the user'
        )
    )
    CAS_ORG_IDS = OrgListField()