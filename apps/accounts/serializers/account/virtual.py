from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import VirtualAccount

__all__ = ['VirtualAccountSerializer']


class VirtualAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualAccount
        field_mini = ['id', 'username', 'name']
        common_fields = ['date_created', 'date_updated']
        fields = field_mini + [
            'secret_from_login', 'comment'
        ] + common_fields
        read_only_fields = ['username'] + common_fields
        extra_kwargs = {
            'comment': {'label': _('Comment')},
            'name': {'label': _('Name')},
            'username': {'label': _('Username')},
        }
