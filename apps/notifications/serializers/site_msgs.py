from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from ..models import SiteMessage


class SenderMixin(ModelSerializer):
    sender = serializers.SerializerMethodField()

    def get_sender(self, site_msg):
        sender = site_msg.sender
        if sender:
            return str(sender)
        else:
            return ''


class SiteMessageDetailSerializer(SenderMixin, ModelSerializer):
    class Meta:
        model = SiteMessage
        fields = [
            'id', 'subject', 'message', 'has_read', 'read_at',
            'date_created', 'date_updated', 'sender',
        ]


class SiteMessageIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField())


class SiteMessageSendSerializer(serializers.Serializer):
    subject = serializers.CharField()
    message = serializers.CharField()
    user_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    group_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    is_broadcast = serializers.BooleanField(default=False)
