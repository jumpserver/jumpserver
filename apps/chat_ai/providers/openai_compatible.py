from urllib.parse import urlparse

import httpx
import openai

from .base import (
    BaseChatProvider, ProviderConfigurationError, ProviderEvent, ProviderError,
    ProviderTimeoutError,
)


def _is_local_url(url):
    if not url:
        return False
    hostname = (urlparse(url).hostname or '').lower()
    return hostname in {'localhost', '127.0.0.1', '::1'} or hostname.endswith('.internal')


class OpenAICompatibleProvider(BaseChatProvider):
    def __init__(
        self, *, base_url, api_key, model, proxy='', timeout=120, max_tokens=4096,
        temperature=0.2, external_models_allowed=True,
    ):
        if not model:
            raise ProviderConfigurationError('Chat AI model is not configured.')
        if not api_key:
            raise ProviderConfigurationError('Chat AI API key is not configured.')
        if not external_models_allowed and not _is_local_url(base_url):
            raise ProviderConfigurationError('External model providers are disabled.')
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.proxy = proxy
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _client(self):
        kwargs = {
            'api_key': self.api_key,
            'base_url': self.base_url,
            'timeout': self.timeout,
        }
        if self.proxy:
            kwargs['http_client'] = httpx.AsyncClient(proxy=self.proxy)
        return openai.AsyncOpenAI(**kwargs)

    async def stream_chat(self, request):
        client = self._client()
        payload = {
            'model': request.get('model') or self.model,
            'messages': request.get('messages') or [],
            'stream': True,
            'stream_options': {'include_usage': True},
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
        }
        if request.get('tools'):
            payload['tools'] = request['tools']
            payload['tool_choice'] = request.get('tool_choice') or 'auto'
        tool_calls = {}
        reasoning_parts = []
        usage = {}
        try:
            while True:
                try:
                    stream = await client.chat.completions.create(**payload)
                    break
                except openai.BadRequestError as exc:
                    error = str(exc).lower()
                    removed_unsupported_option = False
                    for option in ('tool_choice', 'stream_options'):
                        if option in payload and option in error:
                            payload.pop(option, None)
                            removed_unsupported_option = True
                    if not removed_unsupported_option:
                        raise
            async for chunk in stream:
                chunk_usage = getattr(chunk, 'usage', None)
                if chunk_usage:
                    usage = {
                        'input_tokens': getattr(chunk_usage, 'prompt_tokens', 0) or 0,
                        'output_tokens': getattr(chunk_usage, 'completion_tokens', 0) or 0,
                    }
                choices = getattr(chunk, 'choices', None) or []
                if not choices:
                    continue
                delta = choices[0].delta
                reasoning_content = getattr(delta, 'reasoning_content', None)
                if reasoning_content:
                    reasoning_parts.append(reasoning_content)
                if getattr(delta, 'content', None):
                    yield ProviderEvent(kind='delta', content=delta.content)
                for item in getattr(delta, 'tool_calls', None) or []:
                    index = item.index
                    current = tool_calls.setdefault(index, {
                        'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}
                    })
                    if getattr(item, 'id', None):
                        current['id'] = item.id
                    function = getattr(item, 'function', None)
                    if function and getattr(function, 'name', None):
                        current['function']['name'] += function.name
                    if function and getattr(function, 'arguments', None):
                        current['function']['arguments'] += function.arguments
            yield ProviderEvent(
                kind='done',
                reasoning_content=''.join(reasoning_parts),
                tool_calls=[tool_calls[index] for index in sorted(tool_calls)],
                usage=usage,
            )
        except openai.APITimeoutError as exc:
            raise ProviderTimeoutError('Model request timed out.') from exc
        except (openai.APIConnectionError, openai.APIStatusError) as exc:
            raise ProviderError('Model provider is unavailable.') from exc
        finally:
            await client.close()
