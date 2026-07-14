from dataclasses import dataclass, field
from typing import AsyncIterator


class ProviderError(Exception):
    code = 'MODEL_UNAVAILABLE'


class ProviderConfigurationError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    code = 'MODEL_TIMEOUT'


@dataclass
class ProviderEvent:
    kind: str
    content: str = ''
    reasoning_content: str = ''
    tool_calls: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


class BaseChatProvider:
    model = ''

    async def stream_chat(self, request: dict) -> AsyncIterator[ProviderEvent]:
        raise NotImplementedError
