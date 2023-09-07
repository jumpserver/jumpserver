from rest_framework import serializers

from .models import UserPasskey


class PassKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPasskey
        fields = '__all__'
        read_only_fields = ('user', 'credential_id', 'token', 'added_on', 'last_used')
        extra_kwargs = {
            'name': {'required': True},
            'enabled': {'required': True},
            'platform': {'required': True},
        }
