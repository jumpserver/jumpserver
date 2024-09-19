from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from common.utils import convert_html_to_markdown
from ..models import MessageContent


class SenderMixin(ModelSerializer):
    sender = serializers.SerializerMethodField()

    def get_sender(self, site_msg):
        sender = site_msg.sender
        if sender:
            return str(sender)
        else:
            return ''


class MessageContentSerializer(SenderMixin, ModelSerializer):
    message = serializers.SerializerMethodField()

    class Meta:
        model = MessageContent
        fields = [
            'id', 'subject', 'message',
            'date_created', 'date_updated',
            'sender',
        ]

    @staticmethod
    def get_message(site_msg):
        markdown = convert_html_to_markdown(site_msg.message)
        return markdown


class SiteMessageSerializer(SenderMixin, ModelSerializer):
    content = MessageContentSerializer(read_only=True)

    class Meta:
        model = MessageContent
        fields = [
            'id', 'has_read', 'read_at', 'content', 'date_created'
        ]


class SiteMessageIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField())


class SiteMessageSendSerializer(serializers.Serializer):
    subject = serializers.CharField()
    message = serializers.CharField()
    user_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    group_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    is_broadcast = serializers.BooleanField(default=False)
