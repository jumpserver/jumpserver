from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from common.cache import RedisChannelLayer


class RedisChannelLayerTests(IsolatedAsyncioTestCase):
    async def test_brpop_moves_message_to_backup_queue(self):
        layer = RedisChannelLayer(hosts=['redis://localhost'])
        connection = AsyncMock()
        connection.bzpopmin.return_value = (b'channel', b'message', 123)
        manager = AsyncMock()
        manager.__aenter__.return_value = connection

        with patch.object(layer, 'connection', Mock(return_value=manager)):
            message = await layer._brpop_with_clean(0, 'channel', 1)

        self.assertEqual(message, b'message')
        connection.eval.assert_awaited_once()
        connection.zadd.assert_awaited_once_with(
            layer._backup_channel_name('channel'), {b'message': 123.0},
        )
