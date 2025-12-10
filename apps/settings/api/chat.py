from common.api import JMSModelViewSet
from common.permissions import IsValidUser, OnlySuperUser
from .. import serializers
from ..models import ChatPrompt
from ..prompt import DefaultChatPrompt


class ChatPromptViewSet(JMSModelViewSet):
    serializer_classes = {
        'default': serializers.ChatPromptSerializer,
    }
    permission_classes = [IsValidUser]
    queryset = ChatPrompt.objects.all()
    http_method_names = ['get', 'options']
    filterset_fields = ['name']
    search_fields = filterset_fields

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [OnlySuperUser]
        return super().get_permissions()

    def filter_default_prompts(self):
        lang = self.request.LANGUAGE_CODE
        default_prompts = DefaultChatPrompt.get_prompts(lang)
        if not default_prompts:
            return []

        search_query = self.request.query_params.get('search')
        search_query = search_query or self.request.query_params.get('name')
        if not search_query:
            return default_prompts

        search_query = search_query.lower()
        filtered_prompts = [
            prompt for prompt in default_prompts
            if search_query in prompt['name'].lower()
        ]
        return filtered_prompts

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        default_prompts = self.filter_default_prompts()
        return list(queryset) + default_prompts
