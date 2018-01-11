from rest_framework import serializers


class MailTestSerializer(serializers.Serializer):
    EMAIL_HOST = serializers.CharField(max_length=1024, required=True)
    EMAIL_PORT = serializers.IntegerField(default=25)
    EMAIL_HOST_USER = serializers.CharField(max_length=1024)
    EMAIL_HOST_PASSWORD = serializers.CharField()
    EMAIL_USE_SSL = serializers.BooleanField(default=False)
    EMAIL_USE_TLS = serializers.BooleanField(default=False)
