from django.core.validators import RegexValidator
from rest_framework import serializers

__all__ = [
    'FaceCallbackSerializer', 'FaceMonitorCallbackSerializer'
]

from authentication.const import FaceMonitorActionChoices


class FaceCallbackSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, allow_blank=False)
    success = serializers.BooleanField(required=True, allow_null=False)
    error_message = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    face_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class FaceMonitorContextSerializer(serializers.Serializer):
    session_id = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    face_monitor_token = serializers.CharField(required=True, allow_blank=False, allow_null=False)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class FaceMonitorCallbackSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, allow_blank=False)
    is_finished = serializers.BooleanField(required=True)
    success = serializers.BooleanField(required=True)
    error_message = serializers.CharField(required=True, allow_blank=True)
    action = serializers.ChoiceField(required=True, choices=FaceMonitorActionChoices.choices)
    face_codes = serializers.ListField(
        required=False, allow_null=True, allow_empty=True,
        child=serializers.CharField(),
    )

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
