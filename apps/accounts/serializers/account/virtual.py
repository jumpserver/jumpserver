from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import VirtualAccount
from orgs.utils import current_org

__all__ = ['VirtualAccountSerializer']


class VirtualAccountSerializer(serializers.ModelSerializer):
    def validate_alias(self, value):
        org_id = self.instance.org_id if self.instance else current_org.id
        queryset = VirtualAccount.objects.filter(alias=value, org_id=org_id)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(_('This field must be unique.'), code='unique')
        return value

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
            'alias': {'required': True},
        }
