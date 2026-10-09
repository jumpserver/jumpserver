import base64
import re

from rest_framework import serializers


class NonzeroUUIDField(serializers.UUIDField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not value.int:
            self.fail('invalid', value=data)
        return value


class RDPLoginRedeemSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=20, trim_whitespace=False)
    password = serializers.CharField(max_length=43, trim_whitespace=False, write_only=True)

    def validate_username(self, value):
        if not value.isascii() or not re.fullmatch(r'jlt_[a-z2-7]{16}', value.lower()):
            raise serializers.ValidationError('Invalid login credential')
        return value.lower()

    def validate_password(self, value):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
            raise serializers.ValidationError('Invalid login credential')
        decoded = base64.urlsafe_b64decode(value + '=')
        if base64.urlsafe_b64encode(decoded).decode().rstrip('=') != value:
            raise serializers.ValidationError('Invalid login credential')
        return value
