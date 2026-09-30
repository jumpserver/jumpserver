import base64
import re

from rest_framework import serializers


class NonzeroUUIDField(serializers.UUIDField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not value.int:
            self.fail('invalid', value=data)
        return value


class RDPLoginPrepareSerializer(serializers.Serializer):
    connection_token_id = NonzeroUUIDField()


class RDPLoginRedeemSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=20, trim_whitespace=False)
    password = serializers.CharField(max_length=43, trim_whitespace=False, write_only=True)
    redemption_id = NonzeroUUIDField()
    broker_instance_id = NonzeroUUIDField()
    windows_session_id = serializers.IntegerField(min_value=1, max_value=2**32 - 1)

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


class RDPLoginLaunchSerializer(serializers.Serializer):
    launch_grant = serializers.RegexField(
        r'\Ajmsg2_[A-Za-z0-9_-]{43}\Z', max_length=49,
        trim_whitespace=False, write_only=True,
    )
    token_id = NonzeroUUIDField()
    connection_id = NonzeroUUIDField()
    attempt_id = NonzeroUUIDField()
    request_id = NonzeroUUIDField()
    broker_instance_id = NonzeroUUIDField()
    windows_session_id = serializers.IntegerField(min_value=1, max_value=2**32 - 1)
    local_sid = serializers.RegexField(
        r'\AS-1-5-21-(?:[0-9]+-){3}[0-9]+\Z', max_length=184, trim_whitespace=False,
    )
    logon_id = serializers.CharField(max_length=64, trim_whitespace=False)

    def validate_logon_id(self, value):
        if not value.isascii() or not value.isprintable() or value != value.strip():
            raise serializers.ValidationError('Invalid Windows logon ID')
        return value
