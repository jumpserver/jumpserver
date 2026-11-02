import httpx
import openai
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from common.api import JMSModelViewSet
from common.permissions import IsValidUser, OnlySuperUser
from .. import serializers
from ..const import ChatAITypeChoices, ChatAIMethodChoices
from ..connection_testing import get_test_config
from ..models import ChatPrompt
from ..prompt import DefaultChatPrompt


class ChatAITestingAPI(GenericAPIView):
    serializer_class = serializers.ChatAISettingSerializer
    rbac_perms = {
        'POST': 'settings.change_chatai'
    }

    def get_config(self, request):
        return get_test_config(self.serializer_class, request.data)

    def post(self, request):
        config = self.get_config(request)
        chat_ai_enabled = config['CHAT_AI_ENABLED']
        if not chat_ai_enabled:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'msg': _('Chat AI is not enabled')}
            )

        if config['CHAT_AI_METHOD'] != ChatAIMethodChoices.api:
            return Response(
                {'msg': _('Connection testing is only available in API mode')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tp = config['CHAT_AI_TYPE']
        if tp == ChatAITypeChoices.gpt:
            url = config['GPT_BASE_URL']
            api_key = config['GPT_API_KEY']
            proxy = config['GPT_PROXY']
            model = config['GPT_MODEL']
            model = model if config['GPT_MODEL'] != 'custom' else config['CUSTOM_GPT_MODEL']
        else:
            url = config['DEEPSEEK_BASE_URL']
            api_key = config['DEEPSEEK_API_KEY']
            proxy = config['DEEPSEEK_PROXY']
            model = config['DEEPSEEK_MODEL']
            model = model if config['DEEPSEEK_MODEL'] != 'custom' else config['CUSTOM_DEEPSEEK_MODEL']

        if not api_key:
            field = 'GPT_API_KEY' if tp == ChatAITypeChoices.gpt else 'DEEPSEEK_API_KEY'
            raise ValidationError({field: _('This field may not be blank.')})

        kwargs = {
            'base_url': url or None,
            'api_key': api_key,
            'timeout': 30,
            'max_retries': 0,
        }
        client = None
        http_client = None
        ok = False
        error = ''
        try:
            if proxy:
                http_client = httpx.Client(
                    proxy=proxy,
                    transport=httpx.HTTPTransport(local_address='0.0.0.0')
                )
                kwargs['http_client'] = http_client
            client = openai.OpenAI(**kwargs)

            client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": "Say this is a test",
                    }
                ],
                model=model,
            )
            ok = True
        except openai.APIConnectionError as e:
            error = str(e.__cause__)  # an underlying Exception, likely raised within httpx.
        except openai.APIStatusError as e:
            error = str(e.message)
        except Exception as e:
            ok, error = False, str(e)
        finally:
            if client is not None:
                client.close()
            elif http_client is not None:
                http_client.close()

        if ok:
            _status, msg = status.HTTP_200_OK, _('Test success')
        else:
            _status, msg = status.HTTP_400_BAD_REQUEST, error

        return Response(status=_status, data={'msg': msg})


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
