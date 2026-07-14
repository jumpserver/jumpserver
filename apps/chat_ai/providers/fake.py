import asyncio

from .base import BaseChatProvider, ProviderEvent


class FakeProvider(BaseChatProvider):
    def __init__(self, model='fake'):
        self.model = model

    async def stream_chat(self, request):
        last_user_message = next(
            (item.get('content', '') for item in reversed(request.get('messages') or []) if item.get('role') == 'user'),
            '',
        )
        if isinstance(last_user_message, list):
            last_user_message = ' '.join(
                item.get('text', '') for item in last_user_message if item.get('type') == 'text'
            ) or '[image]'
        content = f'Fake provider: {last_user_message}'
        for part in content.split(' '):
            await asyncio.sleep(0)
            yield ProviderEvent(kind='delta', content=part + ' ')
        yield ProviderEvent(
            kind='done',
            usage={'input_tokens': len(last_user_message), 'output_tokens': len(content)},
        )
