from django.template import Engine, TemplateSyntaxError
from rest_framework import serializers

from common.serializers import BulkModelSerializer
from notifications.models import SystemMsgSubscription, UserMsgSubscription


class SystemMsgSubscriptionSerializer(BulkModelSerializer):
    receive_backends = serializers.ListField(child=serializers.CharField())
    message_type_label = serializers.CharField(read_only=True)

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
            'receive_backends': {'required': True}
        }

    def update(self, instance, validated_data):
        instance.set_message_type_label()
        return super().update(instance, validated_data)


class SystemMsgSubscriptionByCategorySerializer(serializers.Serializer):
    category = serializers.CharField()
    category_label = serializers.CharField()
    children = SystemMsgSubscriptionSerializer(many=True)


class UserMsgSubscriptionSerializer(BulkModelSerializer):
    receive_backends = serializers.ListField(child=serializers.CharField(), read_only=False)

    class Meta:
        model = UserMsgSubscription
        fields = ('user_id', 'receive_backends',)


class TemplateEditSerializer(serializers.Serializer):
    EMAIL_TEMPLATE_NAME = serializers.CharField(max_length=256)
    EMAIL_TEMPLATE_CONTENT = serializers.CharField()

    def validate_EMAIL_TEMPLATE_CONTENT(self, value):
        safe_engine = Engine(debug=False, libraries={}, builtins=[])
        try:
            safe_engine.from_string(value)
        except TemplateSyntaxError as e:
            raise serializers.ValidationError(f'Template syntax error at: {e.token.lineno}')
        return value
