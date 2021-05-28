from rest_framework import serializers

from common.drf.serializers import BulkModelSerializer
from .models import SystemMsgSubscription


class SystemMsgSubscriptionSerializer(BulkModelSerializer):
    receive_backends = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = SystemMsgSubscription
        fields = (
            'message_type', 'message_type_label',
            'users', 'groups', 'receive_backends', 'receivers'
        )
        read_only_fields = (
            'message_type', 'message_type_label', 'receivers'
        )
        extra_kwargs = {
            'users': {'allow_empty': True},
            'groups': {'allow_empty': True},
        }


class SystemMsgSubscriptionByCategorySerializer(serializers.Serializer):
    category = serializers.CharField()
    category_label = serializers.CharField()
    children = SystemMsgSubscriptionSerializer(many=True)
