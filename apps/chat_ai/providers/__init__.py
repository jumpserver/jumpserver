from django.conf import settings

from settings.models import get_chat_ai_config

from .base import ProviderConfigurationError
from .fake import FakeProvider
from .openai_compatible import OpenAICompatibleProvider
from .speech import OpenAICompatibleSpeechToTextProvider, SpeechToTextConfigurationError


def get_provider():
    if not settings.CHAT_AI_ENABLED:
        raise ProviderConfigurationError('Chat AI is disabled.')
    if getattr(settings, 'CHAT_AI_METHOD', 'api') != 'api':
        raise ProviderConfigurationError('Built-in Chat AI is disabled in iframe mode.')
    if getattr(settings, 'CHAT_AI_PROVIDER', 'openai_compatible') == 'fake':
        return FakeProvider(model='fake')
    config = get_chat_ai_config()
    return OpenAICompatibleProvider(
        base_url=config.get('base_url') or None,
        api_key=config.get('api_key') or '',
        model=config.get('model') or '',
        proxy=config.get('proxy') or '',
        timeout=getattr(settings, 'CHAT_AI_MODEL_TIMEOUT', 120),
        max_tokens=getattr(settings, 'CHAT_AI_MAX_TOKENS', 4096),
        temperature=getattr(settings, 'CHAT_AI_TEMPERATURE', 0.2),
        external_models_allowed=getattr(settings, 'CHAT_AI_EXTERNAL_MODELS_ALLOWED', True),
    )


def get_transcription_provider():
    if (
        not settings.CHAT_AI_ENABLED
        or getattr(settings, 'CHAT_AI_METHOD', 'api') != 'api'
        or not getattr(settings, 'CHAT_AI_STT_ENABLED', True)
    ):
        raise SpeechToTextConfigurationError('Speech-to-text is disabled.')
    configured_base_url = getattr(settings, 'CHAT_AI_STT_BASE_URL', '') or ''
    configured_api_key = getattr(settings, 'CHAT_AI_STT_API_KEY', '') or ''
    if configured_base_url:
        base_url = configured_base_url
        api_key = configured_api_key or 'local'
        proxy = getattr(settings, 'CHAT_AI_STT_PROXY', '') or ''
    else:
        base_url = getattr(settings, 'CHAT_AI_BASE_URL', '') or None
        api_key = configured_api_key or getattr(settings, 'CHAT_AI_API_KEY', '') or ''
        proxy = getattr(settings, 'CHAT_AI_STT_PROXY', '') or getattr(settings, 'CHAT_AI_PROXY', '') or ''
    return OpenAICompatibleSpeechToTextProvider(
        base_url=base_url,
        api_key=api_key,
        model=getattr(settings, 'CHAT_AI_STT_MODEL', 'whisper-1'),
        proxy=proxy,
        timeout=getattr(settings, 'CHAT_AI_STT_TIMEOUT', 120),
        external_models_allowed=getattr(settings, 'CHAT_AI_EXTERNAL_MODELS_ALLOWED', True),
    )


__all__ = [
    'get_provider', 'get_transcription_provider', 'FakeProvider',
    'OpenAICompatibleProvider', 'OpenAICompatibleSpeechToTextProvider',
]
