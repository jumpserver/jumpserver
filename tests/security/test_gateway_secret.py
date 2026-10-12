import sys
import time
import types
import unittest
from unittest.mock import patch

from django.db.models import TextChoices
from rest_framework import permissions, serializers
from source_boundary import load, settings


class Required(Exception):
    def __init__(self, **kwargs):
        pass


const = load('apps/authentication/const.py', ['ConfirmType'],
             {'TextChoices': TextChoices, '_': lambda x: x})
perms = load('apps/authentication/permissions.py', ['UserConfirmation'],
             {'permissions': permissions, 'settings': settings, 'time': time,
              'ConfirmType': const['ConfirmType'], 'UserConfirmRequired': Required})


class Fields(serializers.Serializer):
    name = serializers.CharField()
    username = serializers.CharField()
    privileged = serializers.BooleanField()
    secret_type = serializers.CharField()
    secret = serializers.CharField()


class SecretMixin:
    pass


serializer = load('apps/assets/serializers/asset/common.py', ['AccountSecretSerializer'],
                  {'SecretReadableMixin': SecretMixin, 'CommonModelSerializer': Fields,
                   'Account': object, 'settings': settings})['AccountSecretSerializer']


class GatewaySecret(unittest.TestCase):
    def render(self, *, authenticated=True, valid=True, permission=True, service=False, session=None, request=True):
        user = types.SimpleNamespace(is_authenticated=authenticated, is_valid=valid,
                                     has_perm=lambda p: permission, is_service_account=service)
        req = types.SimpleNamespace(user=user, session=session or {})
        modules = {
            'authentication.const': types.SimpleNamespace(ConfirmType=const['ConfirmType']),
            'authentication.permissions': types.SimpleNamespace(UserConfirmation=perms['UserConfirmation']),
            'common.exceptions': types.SimpleNamespace(UserConfirmRequired=Required),
        }
        account = dict(name='gateway', username='operator', privileged=False,
                       secret_type='password', secret='synthetic-gateway-secret')
        with patch.dict(sys.modules, modules):
            data = serializer(account, context={'request': req} if request else {}).data
        self.assertEqual({k: v for k, v in data.items() if k != 'secret'},
                         {k: v for k, v in account.items() if k != 'secret'})
        return data['secret']

    def test_low_privilege_invalid_and_missing_context_are_redacted(self):
        for args in ({'permission': False}, {'authenticated': False}, {'valid': False}, {'request': False}):
            self.assertEqual(self.render(**args), '<REDACTED>')

    def test_interactive_secret_policy_and_confirmation_expiry(self):
        self.assertEqual(self.render(), '<REDACTED>')
        now = int(time.time())
        confirmed = dict(CONFIRM_LEVEL=3, CONFIRM_TYPE='mfa', CONFIRM_TIME=now)
        self.assertEqual(self.render(session=confirmed), 'synthetic-gateway-secret')
        self.assertEqual(self.render(session={**confirmed, 'CONFIRM_TIME': now - 61}), '<REDACTED>')
        self.assertEqual(self.render(session={**confirmed, 'CONFIRM_LEVEL': 2}), '<REDACTED>')
        with patch.object(settings, 'SECURITY_ACCOUNT_SECRET_READ', False):
            self.assertEqual(self.render(session=confirmed), '<REDACTED>')

    def test_component_secret_permission_is_still_required(self):
        self.assertEqual(self.render(service=True), 'synthetic-gateway-secret')
        self.assertEqual(self.render(service=True, permission=False), '<REDACTED>')
        self.assertEqual(self.render(service=True, valid=False), '<REDACTED>')
        with patch.object(settings, 'SECURITY_DISABLE_VIEW_SECRET', True, create=True):
            self.assertEqual(self.render(service=True), '<REDACTED>')
            self.assertEqual(self.render(session=dict(CONFIRM_LEVEL=3, CONFIRM_TYPE='mfa',
                                                     CONFIRM_TIME=int(time.time()))), '<REDACTED>')
