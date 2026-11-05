from rest_framework import serializers

from .models import AuditConversation, AuditMessage


class AuditMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditMessage
        fields = (
            'id', 'role', 'content', 'status', 'error',
            'input_tokens', 'output_tokens', 'date_created',
        )


class AuditConversationSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    message_count = serializers.IntegerField(read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    last_question_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = AuditConversation
        fields = (
            'id', 'title', 'assistant', 'profile', 'status', 'user', 'message_count',
            'question_count', 'last_question_at', 'date_created', 'date_updated',
        )

    @staticmethod
    def get_user(obj):
        return {'id': str(obj.subject_id), 'name': obj.subject_name, 'username': obj.subject_username}


class AuditConversationDetailSerializer(AuditConversationSerializer):
    messages = AuditMessageSerializer(many=True, read_only=True)

    class Meta(AuditConversationSerializer.Meta):
        fields = AuditConversationSerializer.Meta.fields + ('messages',)


class AuditConversationInput(serializers.ModelSerializer):
    id = serializers.UUIDField()

    class Meta:
        model = AuditConversation
        exclude = ('source_revision',)
        extra_kwargs = {'title': {'allow_blank': True}}


class AuditMessageInput(serializers.ModelSerializer):
    id = serializers.CharField(max_length=128, trim_whitespace=False)
    conversation_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=('user', 'assistant'))

    class Meta:
        model = AuditMessage
        exclude = ('conversation', 'source_revision')


class AuditProjectionInput(serializers.Serializer):
    version = serializers.IntegerField(min_value=1, max_value=1)
    conversations = AuditConversationInput(many=True, required=False, default=list)
    messages = AuditMessageInput(many=True, required=False, default=list)
