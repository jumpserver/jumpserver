from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import VirtualAccount

__all__ = ['VirtualAccountSerializer']


class VirtualAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualAccount
        field_mini = ['id', 'alias', 'username', 'name']
        common_fields = ['date_created', 'date_updated', 'comment']
        fields = field_mini + [
            'secret_from_login',
        ] + common_fields
        read_only_fields = common_fields + common_fields
        extra_kwargs = {
            'comment': {'label': _('Comment')},
            'name': {'label': _('Name')},
            'username': {'label': _('Username')},
            'secret_from_login': {
                'help_text': _(
                    'Current only support login from AD/LDAP. Secret priority: '
                    'Same account in asset secret > Login secret > Manual input. <br/ >'
                    'For security, please set config CACHE_LOGIN_PASSWORD_ENABLED to true'
                )
            },
            'alias': {'required': False},
        }
