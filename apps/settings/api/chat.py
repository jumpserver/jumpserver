import re

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

    @classmethod
    def get_error_response(cls, error):
        detail = cls.get_error_detail(error)
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={'detail': detail},
        )

    @classmethod
    def get_error_detail(cls, error):
        if isinstance(error, openai.APITimeoutError):
            return _(
                'The connection to the model provider timed out. Please check '
                'the Base URL, proxy, and network.'
            )

        if isinstance(error, openai.APIConnectionError):
            cause = str(error.__cause__ or error).lower()
            if any(word in cause for word in (
                'certificate verify', 'certificate_verify', 'ssl',
            )):
                return _(
                    'The model provider certificate verification failed. '
                    'Please check its HTTPS certificate.'
                )
            if any(word in cause for word in (
                'getaddrinfo', 'name or service not known',
                'nodename nor servname', 'temporary failure in name resolution',
            )):
                return _(
                    'The model provider hostname could not be resolved. Please '
                    'check the Base URL and DNS settings.'
                )
            if 'connection refused' in cause:
                return _(
                    'The model provider refused the connection. Please check '
                    'the Base URL, port, and service status.'
                )
            return _(
                'Unable to connect to the model provider. Please check the Base '
                'URL, proxy, and network.'
            )

        if isinstance(error, openai.APIStatusError):
            provider_detail, error_code, error_type = cls.get_provider_error(error)
            fingerprint = ' '.join(filter(None, (
                error_code,
                error_type,
                provider_detail,
            ))).lower()
            status_code = getattr(error, 'status_code', None)

            if status_code == 402 or any(word in fingerprint for word in (
                'insufficient balance', 'insufficient_balance',
                'insufficient quota', 'insufficient_quota',
            )):
                return _(
                    'The model provider account has insufficient balance. '
                    'Please recharge it and try again.'
                )
            if status_code == 401 or any(word in fingerprint for word in (
                'invalid_api_key', 'authentication', 'unauthorized',
            )):
                return _(
                    'Authentication with the model provider failed. Please '
                    'check the API key.'
                )
            if status_code == 403:
                return _(
                    'The model provider denied access. Please check the API key '
                    'permissions.'
                )
            if any(word in fingerprint for word in (
                'model_not_found', 'model not found', 'unknown model',
                'model does not exist',
            )):
                return _(
                    'The selected model does not exist or is unavailable. '
                    'Please check the model and Base URL.'
                )
            if status_code == 404:
                return _(
                    'The model provider endpoint was not found. Please check '
                    'the Base URL.'
                )
            if status_code == 429:
                return _(
                    'The model provider request limit was exceeded. Please try '
                    'again later.'
                )
            if status_code and status_code >= 500:
                return _(
                    'The model provider service is temporarily unavailable. '
                    'Please try again later.'
                )
            if provider_detail:
                return _(
                    'Model provider request failed (HTTP {status_code}): '
                    '{detail}'
                ).format(
                    status_code=status_code or '-',
                    detail=provider_detail,
                )
            return _('Model provider request failed (HTTP {status_code}).').format(
                status_code=status_code or '-',
            )

        return str(error) or _('Unable to connect to the model provider')

    @staticmethod
    def get_provider_error(error):
        body = getattr(error, 'body', None)
        if isinstance(body, dict):
            body = body.get('error', body)
            if isinstance(body, dict):
                detail = str(body.get('message') or '').strip()
                code = str(body.get('code') or '').strip()
                error_type = str(body.get('type') or '').strip()
                return detail, code, error_type
            if body:
                return str(body).strip(), '', ''

        message = str(getattr(error, 'message', '') or '').strip()
        message = re.sub(r'^Error code:\s*\d+\s*-\s*', '', message)
        if message.startswith(('{', '[')):
            message = ''
        return message, '', ''


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
