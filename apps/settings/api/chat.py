import httpx
import openai
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from .. import serializers


class ChatAIProviderMixin:
    serializer_class = serializers.ChatAISettingSerializer
    rbac_perms = {
        'POST': 'settings.change_chatai'
    }

    def get_config(self, request):
        serializer = self.serializer_class(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return {
            'base_url': data.get('CHAT_AI_BASE_URL') or settings.CHAT_AI_BASE_URL or None,
            'api_key': data.get('CHAT_AI_API_KEY') or settings.CHAT_AI_API_KEY or '',
            'proxy': data.get('CHAT_AI_PROXY') or settings.CHAT_AI_PROXY or '',
            'model': data.get('CHAT_AI_MODEL') or settings.CHAT_AI_MODEL or '',
        }

    @staticmethod
    def get_client(config):
        kwargs = {
            'base_url': config['base_url'],
            'api_key': config['api_key'] or 'not-required',
            'timeout': settings.CHAT_AI_MODEL_TIMEOUT,
        }
        if config['proxy']:
            kwargs['http_client'] = httpx.Client(proxy=config['proxy'])
        return openai.OpenAI(**kwargs)

    @staticmethod
    def get_error_response(error):
        if isinstance(error, openai.APIStatusError):
            detail = error.message
        elif isinstance(error, openai.APIConnectionError):
            detail = str(error.__cause__ or error)
        else:
            detail = str(error)
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={'detail': detail or _('Unable to connect to the model provider')},
        )


class ChatAIModelsAPI(ChatAIProviderMixin, GenericAPIView):
    def post(self, request):
        config = self.get_config(request)
        client = None
        try:
            client = self.get_client(config)
            response = client.models.list()
            model_ids = sorted({
                str(item.id) for item in response.data
                if getattr(item, 'id', None)
            })
        except Exception as error:
            return self.get_error_response(error)
        finally:
            if client is not None:
                client.close()

        models = [{'id': model_id, 'label': model_id} for model_id in model_ids]
        return Response({'count': len(models), 'models': models})


class ChatAITestingAPI(ChatAIProviderMixin, GenericAPIView):

    def post(self, request):
        config = self.get_config(request)
        if not config['model']:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': _('Please select or enter a model first')},
            )

        client = None
        try:
            client = self.get_client(config)
            response = client.chat.completions.create(
                messages=[
                    {
                        'role': 'user',
                        'content': (
                            'Call the provided tool to obtain the JumpServer '
                            'health-check nonce. Do not answer without calling it.'
                        ),
                    }
                ],
                model=config['model'],
                tools=[
                    {
                        'type': 'function',
                        'function': {
                            'name': 'get_jumpserver_health_check_nonce',
                            'description': (
                                'Return the private nonce required to complete '
                                'the JumpServer model capability test.'
                            ),
                            'parameters': {
                                'type': 'object',
                                'properties': {},
                                'additionalProperties': False,
                            },
                        },
                    }
                ],
            )
            tool_calls = response.choices[0].message.tool_calls
            if not tool_calls:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={
                        'detail': _(
                            'The provider is reachable, but the selected model '
                            'does not support the required tool calls'
                        )
                    },
                )
        except Exception as error:
            return self.get_error_response(error)
        finally:
            if client is not None:
                client.close()

        return Response({
            'msg': _('Test success'),
            'model': config['model'],
            'tool_calls': True,
        })
