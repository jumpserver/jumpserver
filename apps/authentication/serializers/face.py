from rest_framework import serializers

__all__ = [
    'FaceCallbackSerializer'
]


class FaceCallbackSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, allow_blank=False)
    success = serializers.BooleanField(required=True, allow_null=False)
    error_message = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    face_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
