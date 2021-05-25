from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from .models import SiteMessage


class SiteMessageListSerializer(ModelSerializer):
    class Meta:
        model = SiteMessage
        fields = ['subject', 'has_read', 'read_at']


class SiteMessageRetrieveSerializer(ModelSerializer):
    class Meta:
        model = SiteMessage
        fields = ['subject', 'message', 'has_read', 'read_at']


class SiteMessageIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField())


class SiteMessageSendSerializer(serializers.Serializer):
    subject = serializers.CharField()
    message = serializers.CharField()
    user_ids = serializers.ListField(child=serializers.UUIDField())
    group_ids = serializers.ListField(child=serializers.UUIDField())
    is_broadcast = serializers.BooleanField(default=False)
