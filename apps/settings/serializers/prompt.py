from rest_framework import serializers

from settings.models import ChatPrompt


class ChatPromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatPrompt
        fields = [
            'id', 'name', 'content', 'builtin'
        ]
