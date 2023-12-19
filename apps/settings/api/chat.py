import httpx
import openai
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from common.api import JMSModelViewSet
from common.permissions import IsValidUser, OnlySuperUser
from .. import serializers
from ..models import ChatPrompt
from ..prompt import DefaultChatPrompt


class ChatAITestingAPI(GenericAPIView):
    serializer_class = serializers.ChatAISettingSerializer
    rbac_perms = {
        'POST': 'settings.change_chatai'
    }

    def get_config(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = self.serializer_class().data
        data.update(serializer.validated_data)
        for k, v in data.items():
            if v:
                continue
            # 页面没有传递值, 从 settings 中获取
            data[k] = getattr(settings, k, None)
        return data

    def post(self, request):
        config = self.get_config(request)
        chat_ai_enabled = config['CHAT_AI_ENABLED']
        if not chat_ai_enabled:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'msg': _('Chat AI is not enabled')}
            )

        proxy = config['GPT_PROXY']
        model = config['GPT_MODEL']

        kwargs = {
            'base_url': config['GPT_BASE_URL'] or None,
            'api_key': config['GPT_API_KEY'],
        }
        try:
            if proxy:
                kwargs['http_client'] = httpx.Client(
                    proxies=proxy,
                    transport=httpx.HTTPTransport(local_address='0.0.0.0')
                )
            client = openai.OpenAI(**kwargs)

            ok = False
            error = ''

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
