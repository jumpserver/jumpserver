from common.drf.serializers import BulkModelSerializer
from .models import Backend, Message
from rest_framework import serializers


class BackendSerializer(BulkModelSerializer):
    name_display = serializers.CharField(source='get_name_display')

    class Meta:
        model = Backend
        fields = ('id', 'name', 'name_display')


class MessageSerializer(BulkModelSerializer):
    class Meta:
        model = Message
        fields = (
            'id', 'app', 'message', 'app_label', 'message_label',
            'users', 'groups', 'receive_backends', 'receivers'
        )
        read_only_fields = (
            'app', 'message', 'app_label', 'message_label', 'receivers'
        )
        extra_kwargs = {
            'users': {'allow_empty': True},
            'receive_backends': {'allow_empty': True}
        }
