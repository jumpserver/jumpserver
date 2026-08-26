import asyncio
import ipaddress
from urllib.parse import urlparse

import httpx
import openai


def is_local_provider_url(url):
    if not url:
        return False
    hostname = (urlparse(url).hostname or '').lower()
    if not hostname:
        return False
    if hostname in {'localhost', '127.0.0.1', '::1'} or hostname.endswith('.internal'):
        return True
    if '.' not in hostname:
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


class SpeechToTextError(Exception):
    code = 'TRANSCRIPTION_FAILED'


class SpeechToTextConfigurationError(SpeechToTextError):
    code = 'SPEECH_MODEL_UNAVAILABLE'


class SpeechToTextTimeoutError(SpeechToTextError):
    code = 'SPEECH_MODEL_TIMEOUT'


class SpeechToTextInputError(SpeechToTextError):
    code = 'invalid_audio'


class SpeechToTextRateLimitError(SpeechToTextError):
    code = 'SPEECH_MODEL_RATE_LIMITED'


class OpenAICompatibleSpeechToTextProvider:
    def __init__(
        self, *, base_url, api_key, model, proxy='', timeout=120,
        external_models_allowed=True,
    ):
        if not model:
            raise SpeechToTextConfigurationError('Speech-to-text model is not configured.')
        if not api_key:
            raise SpeechToTextConfigurationError('Speech-to-text API key is not configured.')
        if not external_models_allowed and not is_local_provider_url(base_url):
            raise SpeechToTextConfigurationError('External speech-to-text providers are disabled.')
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.proxy = proxy
        self.timeout = timeout

    def _client(self):
        kwargs = {
            'api_key': self.api_key,
            'base_url': self.base_url,
            'timeout': self.timeout,
        }
        if self.proxy:
            kwargs['http_client'] = httpx.AsyncClient(proxy=self.proxy)
        return openai.AsyncOpenAI(**kwargs)

    async def transcribe(self, *, file, filename, content_type, language=''):
        client = self._client()
        payload = {
            'file': (filename, file, content_type),
            'model': self.model,
        }
        if language:
            payload['language'] = language
        try:
            async with asyncio.timeout(self.timeout):
                result = await client.audio.transcriptions.create(**payload)
            text = result if isinstance(result, str) else getattr(result, 'text', '')
            if not isinstance(text, str) or not text.strip():
                raise SpeechToTextError('Speech-to-text provider returned an empty result.')
            result_language = getattr(result, 'language', '') if not isinstance(result, str) else ''
            return {
                'text': text.strip(),
                'language': str(result_language or language or ''),
            }
        except (TimeoutError, openai.APITimeoutError) as exc:
            raise SpeechToTextTimeoutError('Speech-to-text request timed out.') from exc
        except openai.BadRequestError as exc:
            raise SpeechToTextInputError('Audio could not be transcribed.') from exc
        except openai.RateLimitError as exc:
            raise SpeechToTextRateLimitError('Speech-to-text provider rate limit was exceeded.') from exc
        except (
            openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError,
        ) as exc:
            raise SpeechToTextConfigurationError('Speech-to-text provider is unavailable.') from exc
        except (openai.APIConnectionError, openai.APIStatusError, openai.OpenAIError) as exc:
            raise SpeechToTextError('Speech-to-text provider is unavailable.') from exc
        finally:
            await client.close()
