from rest_framework import serializers

from .models import Passkey


class PasskeySerializer(serializers.ModelSerializer):
    class Meta:
        model = Passkey
        fields = [
            'id', 'name', 'is_active', 'platform', 'created_by',
            'date_last_used', 'date_created',
        ]
        read_only_fields = list(set(fields) - {'is_active'})
