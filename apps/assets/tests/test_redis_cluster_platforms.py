from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from assets.const.database import DatabaseTypes
from assets.models import Platform
from authentication.serializers.connect_token_secret import _ConnectionTokenPlatformSerializer


class RedisClusterPlatformTests(TestCase):
    def test_builtin_protocol_in_connection_token(self):
        templates = {p['name']: p['protocols_setting']['redis']
                     for p in DatabaseTypes.internal_platforms()[DatabaseTypes.REDIS]}
        request = Request(APIRequestFactory().get('/api/v1/authentication/connection-token/'))
        for name, username, cluster in (
            ('Redis', False, False), ('Redis6+', True, False),
            ('Redis-Cluster', False, True), ('Redis-Cluster-ACL', True, True),
        ):
            with self.subTest(name=name):
                platform = Platform.objects.get(name=name, internal=True, type='redis')
                data = _ConnectionTokenPlatformSerializer(platform, context={'request': request}).data
                protocol, = data['protocols']
                self.assertEqual(protocol['name'], 'redis')
                for setting in (protocol['setting'], templates[name]):
                    self.assertIs(setting['auth_username'], username)
                    self.assertIs(setting.get('enable_cluster_mode', False), cluster)

    def test_migration_is_idempotent_and_preserves_custom_platform(self):
        migrate = import_module('assets.migrations.0036_redis_cluster_platforms').add_redis_cluster_platforms
        custom = Platform.objects.get(name='Redis-Cluster')
        custom.internal = False
        custom.save(update_fields=['internal'])
        custom.protocols.update(port=17000, setting={'auth_username': True})
        editor = SimpleNamespace(connection=connection)
        migrate(apps, editor)
        migrate(apps, editor)
        protocol = custom.protocols.get()
        self.assertEqual(protocol.port, 17000)
        self.assertEqual(protocol.setting, {'auth_username': True})
        self.assertEqual(Platform.objects.get(name='Redis-Cluster-ACL').protocols.count(), 1)
