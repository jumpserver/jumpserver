from rest_framework import serializers

from accounts.models import VirtualAccount

__all__ = ['VirtualAccountSerializer']


class VirtualAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualAccount
        field_mini = ['id', 'username']
        fields = field_mini + [
            'secret_from_login', 'date_created', 'date_updated'
        ]
