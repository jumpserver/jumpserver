import json
import re
import secrets

import httpx
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
        import openai

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
        import openai

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
    tool_name = 'get_jumpserver_health_check_nonce'

    @classmethod
    def get_error_detail(cls, error):
        import openai

        detail = super().get_error_detail(error)
        if isinstance(error, openai.APIStatusError) and error.status_code in (404, 405, 501):
            return _(
                '{detail} The provider must support the Responses API (/responses).'
            ).format(detail=detail)
        return detail

    @staticmethod
    def stream_response(client, model, inputs, tools):
        output = {}
        text_deltas = {}
        argument_deltas = {}
        completed = None
        with client.responses.create(
            model=model, input=inputs, tools=tools, stream=True, store=False,
            include=['reasoning.encrypted_content'],
        ) as stream:
            content_type = stream.response.headers.get('content-type', '')
            if content_type.split(';', 1)[0].strip().lower() != 'text/event-stream':
                raise ValueError(_(
                    'The provider did not return a Responses API event stream.'
                ))

            for event in stream:
                if event.type == 'error':
                    raise ValueError(_(
                        'The Responses API stream failed: {detail}'
                    ).format(detail=event.message))
                if event.type in ('response.failed', 'response.incomplete'):
                    error = getattr(event.response, 'error', None)
                    incomplete = getattr(event.response, 'incomplete_details', None)
                    detail = (
                        getattr(error, 'message', None) or
                        getattr(incomplete, 'reason', None) or event.type
                    )
                    raise ValueError(_(
                        'The Responses API stream failed: {detail}'
                    ).format(detail=detail))
                if event.type == 'response.output_item.done':
                    output[event.output_index] = event.item.model_dump(exclude_none=True)
                elif event.type == 'response.output_text.delta':
                    key = (event.output_index, event.content_index)
                    text_deltas[key] = text_deltas.get(key, '') + event.delta
                elif event.type == 'response.function_call_arguments.delta':
                    key = event.output_index
                    argument_deltas[key] = argument_deltas.get(key, '') + event.delta
                elif event.type == 'response.completed':
                    completed = event.response
                    break

        if (
            completed is None or completed.status != 'completed' or
            getattr(completed, 'error', None)
        ):
            raise ValueError(_(
                'The Responses API stream ended without a successful completion event.'
            ))

        expected_text = {}
        for index, item in output.items():
            if item.get('status') not in (None, 'completed'):
                raise ValueError(_(
                    'The Responses API stream returned an incomplete output item.'
                ))
            if item['type'] == 'message':
                for content_index, content in enumerate(item['content']):
                    if content['type'] == 'output_text' and content['text']:
                        expected_text[index, content_index] = content['text']

        if expected_text != {key: value for key, value in text_deltas.items() if value}:
            raise ValueError(_(
                'The Responses API text stream is missing or does not match the final output.'
            ))
        for index, arguments in argument_deltas.items():
            item = output.get(index, {})
            if item.get('type') != 'function_call' or item.get('arguments') != arguments:
                raise ValueError(_(
                    'The Responses API tool argument stream does not match the final tool call.'
                ))
        return [output[index] for index in sorted(output)], ''.join(
            expected_text[key] for key in sorted(expected_text)
        )

    @classmethod
    def validate_tool_call(cls, output):
        tool_calls = [item for item in output if item['type'] == 'function_call']
        if not tool_calls:
            raise ValueError(_(
                'The provider is reachable, but the selected model '
                'does not support the required tool calls'
            ))
        if len(tool_calls) == 1:
            call = tool_calls[0]
            try:
                arguments = json.loads(call.get('arguments', ''))
            except (TypeError, ValueError):
                arguments = None
            call_id = call.get('call_id')
            if (
                call.get('name') == cls.tool_name and
                isinstance(call_id, str) and call_id.strip() and arguments == {}
            ):
                return call
        raise ValueError(_(
            'The Responses API returned an invalid health-check tool call '
            '(name, call ID, or arguments).'
        ))

    def post(self, request):
        config = self.get_config(request)
        if not config['model']:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': _('Please select or enter a model first')},
            )

        client = None
        try:
            client = self.get_client(config).with_options(max_retries=0)
            inputs = [{
                'role': 'user',
                'content': (
                    'Call get_jumpserver_health_check_nonce exactly once with '
                    'no arguments to obtain the JumpServer health-check nonce. '
                    'Do not answer without calling it. After receiving the tool '
                    'result, reply with only the exact value of result.nonce, '
                    'without any other text, quotes, or formatting.'
                ),
            }]
            tools = [{
                'type': 'function',
                'name': self.tool_name,
                'description': (
                    'Return the private nonce required to complete '
                    'the JumpServer model capability test.'
                ),
                'parameters': {
                    'type': 'object',
                    'properties': {},
                    'required': [],
                    'additionalProperties': False,
                },
            }]
            output, _text = self.stream_response(client, config['model'], inputs, tools)
            call = self.validate_tool_call(output)

            # Replay the complete output, including reasoning, as Kael/Codex does.
            # Only the tool result contains the nonce, so an echo proves receipt.
            nonce = secrets.token_hex(16)
            inputs.extend(output)
            inputs.append({
                'type': 'function_call_output',
                'call_id': call['call_id'],
                'output': json.dumps({'status': 'success', 'result': {'nonce': nonce}}),
            })
            output, text = self.stream_response(client, config['model'], inputs, tools)
            if any(item['type'] == 'function_call' for item in output) or text.strip() != nonce:
                raise ValueError(_(
                    'The model did not correctly return the health-check nonce '
                    'after receiving the tool result.'
                ))
        except Exception as error:
            return self.get_error_response(error)
        finally:
            if client is not None:
                client.close()

        return Response({
            'msg': _('Test success'),
            'model': config['model'],
            'responses': True,
            'tool_calls': True,
            'streaming': True,
            'tool_result': True,
        })
