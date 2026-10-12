import base64
import json
import io
import sys
import types
import unittest
from unittest.mock import patch

from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes
from Cryptodome.Util.Padding import pad
from django.core.cache import cache
from django.core.management.base import BaseCommand
from itsdangerous import JSONWebSignatureSerializer, BadSignature
from source_boundary import RedisFixture, load, settings

crypto = load('apps/common/utils/crypto/rsa_aes.py', ['AESCryptoGCM', 'get_aes_crypto'],
              dict(base64=base64, AES=AES, get_random_bytes=get_random_bytes, pad=pad, settings=settings))
encoding = load('apps/common/utils/encode.py', ['Singleton', 'Signer'],
                dict(JSONWebSignatureSerializer=JSONWebSignatureSerializer, BadSignature=BadSignature))
signer = encoding['Signer'](settings.SECRET_KEY)
# Prime lazy native crypto imports before patch.dict restores sys.modules.
crypto['get_aes_crypto']().encrypt('fixture-initialization')
Auth = load('apps/users/models/user/_auth.py', ['AuthMixin'],
            dict(json=json, cache=cache, settings=settings),
            members=['cache_login_password_if_need', 'get_cached_password_if_has', '_get_cached_password'])['AuthMixin']
Auth.sect_cache_tpl = 'user_sect_{}'


class PasswordCache(RedisFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.user = Auth()
        self.user.id = 'fixture-user'
        self.user.backend = 'authentication.backends.ldap.LDAPBackend'
        self.key = self.user.sect_cache_tpl.format(self.user.id)
        self.modules = patch.dict(sys.modules, {
            'common.utils': types.SimpleNamespace(signer=signer),
            'common.utils.crypto': types.SimpleNamespace(get_aes_crypto=crypto['get_aes_crypto']),
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def test_encrypted_random_roundtrip_and_business_gates(self):
        password = 'isolated-test-口令-123'
        self.user.cache_login_password_if_need(password)
        first = cache.get(self.key)
        self.assertTrue(first.startswith('aes-gcm:v1:'))
        self.assertNotIn(password, first)
        self.assertEqual(self.user.get_cached_password_if_has(), password)
        self.user.cache_login_password_if_need(password)
        self.assertNotEqual(first, cache.get(self.key))
        self.assertGreater(cache.ttl(self.key), 0)
        with patch.object(settings, 'CACHE_LOGIN_PASSWORD_ENABLED', False):
            self.assertEqual(self.user.get_cached_password_if_has(), '')
        self.user.backend = 'model'
        cache.delete(self.key)
        self.user.cache_login_password_if_need(password)
        self.assertIsNone(cache.get(self.key))

    def test_tampering_cross_user_and_invalid_payload_fail_closed(self):
        cipher = crypto['get_aes_crypto']()
        for payload in ({'user_id': 'another-user', 'password': 'test'}, {'user_id': self.user.id, 'password': 9}, []):
            cache.set(self.key, 'aes-gcm:v1:' + cipher.encrypt(json.dumps(payload)), 30)
            self.assertEqual(self.user.get_cached_password_if_has(), '')
            self.assertIsNone(cache.get(self.key))
        self.user.cache_login_password_if_need('synthetic-test')
        original = cache.get(self.key)
        for data in ('aes-gcm:v1:invalid', original[:35] + ('A' if original[35] != 'A' else 'B') + original[36:], 'invalid-signature', 99, ['invalid-cache']):
            cache.set(self.key, data, 30)
            self.assertEqual(self.user.get_cached_password_if_has(), '')
            self.assertIsNone(cache.get(self.key))

    def test_legacy_signed_entry_migrates_without_extending_ttl(self):
        cache.set(self.key, signer.sign('synthetic-legacy'), 20)
        self.assertEqual(self.user.get_cached_password_if_has(), 'synthetic-legacy')
        self.assertTrue(cache.get(self.key).startswith('aes-gcm:v1:'))
        self.assertLessEqual(cache.ttl(self.key), 20)
        self.assertEqual(self.user.get_cached_password_if_has(), 'synthetic-legacy')

    def test_upgrade_command_migrates_unvisited_entries_even_when_disabled(self):
        def user_factory(id):
            user = Auth()
            user.id = id
            return user
        user_factory.sect_cache_tpl = Auth.sect_cache_tpl
        Command = load('apps/common/management/commands/encrypt_login_password_cache.py', ['Command'],
                       dict(BaseCommand=BaseCommand, cache=cache, User=user_factory,
                            signer=signer, get_aes_crypto=crypto['get_aes_crypto']))['Command']
        cache.set(self.key, signer.sign('synthetic-unvisited'), 20)
        cache.set('unrelated-fixture', 'leave-this-alone', 20)
        cache.set('user_sect_invalid', 'invalid-signature', 20)
        output = io.StringIO()
        with patch.object(settings, 'CACHE_LOGIN_PASSWORD_ENABLED', False):
            Command(stdout=output).handle()
        self.assertTrue(cache.get(self.key).startswith('aes-gcm:v1:'))
        self.assertLessEqual(cache.ttl(self.key), 20)
        self.assertEqual(cache.get('unrelated-fixture'), 'leave-this-alone')
        self.assertIsNone(cache.get('user_sect_invalid'))
        self.assertNotIn('synthetic-unvisited', output.getvalue())
        self.assertEqual(self.user.get_cached_password_if_has(), 'synthetic-unvisited')
