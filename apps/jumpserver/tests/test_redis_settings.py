import json
import os
import subprocess
import sys
from unittest import TestCase


SETTINGS_PROBE = '''
import json
import sys
from copy import deepcopy
from unittest.mock import patch

from jumpserver.conf import Config, ConfigManager

overrides = json.loads(sys.stdin.read())
order = overrides.pop('_pool_order', ['default', 'session', 'blocking'])
config = Config({
    'SECRET_KEY': 'redis-settings-test-key',
    'BOOTSTRAP_TOKEN': 'redis-settings-test-token',
    **overrides,
})
config.compatible()
with patch.object(ConfigManager, 'load_user_config', return_value=config):
    from jumpserver import settings

from django.conf import settings as django_settings
django_settings.configure(default_settings=settings)
from django_redis.pool import get_connection_factory

pools = {}
clients = {}
for alias in order:
    cache = settings.CACHES[alias]
    options = deepcopy(cache['OPTIONS'])
    client = get_connection_factory(options=options).connect(cache['LOCATION'])
    clients[alias] = client
    connection = client.connection_pool.make_connection()
    pools[alias] = {
        'socket_timeout': connection.socket_timeout,
        'socket_connect_timeout': connection.socket_connect_timeout,
        'health_check_interval': connection.health_check_interval,
        'socket_keepalive': connection.socket_keepalive,
        'retry_on_timeout': connection.retry_on_timeout,
        'connection_class': type(connection).__name__,
        'client_class': type(client).__module__,
    }

print(json.dumps({
    'pools': pools,
    'isolated': clients['default'].connection_pool is not clients['blocking'].connection_pool,
}))
'''


class RedisSettingsTests(TestCase):
    def probe(self, **overrides):
        return subprocess.run(
            [sys.executable, '-c', SETTINGS_PROBE], input=json.dumps(overrides),
            capture_output=True, text=True, timeout=30,
            env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'jumpserver.settings'},
        )

    def test_isolated_pools_support_direct_tls_and_sentinel(self):
        for tls in (False, True):
            for sentinel in (False, True):
                for blocking_first in (False, True):
                    with self.subTest(tls=tls, sentinel=sentinel, blocking_first=blocking_first):
                        order = ['default', 'session', 'blocking']
                        if blocking_first:
                            order.reverse()
                        result = self.probe(
                            REDIS_USE_SSL=tls,
                            REDIS_SENTINEL_HOSTS='test-primary/127.0.0.1:26379' if sentinel else '',
                            _pool_order=order,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        config = json.loads(result.stdout)
                        self.assertTrue(config['isolated'])
                        for alias, pool in config['pools'].items():
                            self.assertEqual(pool['socket_timeout'], None if alias == 'blocking' else 5)
                            self.assertEqual(pool['socket_connect_timeout'], 5)
                            self.assertEqual(pool['health_check_interval'], 30)
                            self.assertTrue(pool['socket_keepalive'])
                            self.assertFalse(pool['retry_on_timeout'])
                            self.assertEqual(pool['client_class'], 'redis.client')
                            self.assertEqual('SSL' in pool['connection_class'], tls)
                            self.assertEqual('Sentinel' in pool['connection_class'], sentinel)

    def test_fractional_timeouts_are_configurable(self):
        result = self.probe(REDIS_SOCKET_TIMEOUT=0.5, REDIS_SOCKET_CONNECT_TIMEOUT=1.5)
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout)
        for alias in ('default', 'session'):
            self.assertEqual(config['pools'][alias]['socket_timeout'], 0.5)
            self.assertEqual(config['pools'][alias]['socket_connect_timeout'], 1.5)
        self.assertIsNone(config['pools']['blocking']['socket_timeout'])
        self.assertEqual(config['pools']['blocking']['socket_connect_timeout'], 1.5)

    def test_invalid_timeouts_fail_at_startup(self):
        for key, value in (
            ('REDIS_SOCKET_TIMEOUT', 0),
            ('REDIS_SOCKET_CONNECT_TIMEOUT', -1),
            ('REDIS_SOCKET_TIMEOUT', 'nan'),
        ):
            with self.subTest(key=key, value=value):
                result = self.probe(**{key: value})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'{key} must be a positive finite number', result.stderr)
