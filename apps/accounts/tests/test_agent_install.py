import os
import pwd
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from django.core import signing
from django.db import transaction
from django.test import SimpleTestCase
from rest_framework.permissions import AllowAny

from accounts.api.account.credential import CredentialClientViewSet
from accounts.demos.python.jms_pam.agent import Agent, atomic_write_json, install, read_json, register
from accounts.demos.python.jms_pam.main import JumpServerPAMClient
from accounts.models import ClientAccessConfiguration, CredentialClientInstance
from accounts.tests.base import CredentialTestCase


class RegistrationIdentityTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Agent', type='agent', app_user='app',
        )

    def register(self, nonce, instance='agent'):
        token = signing.dumps({
            'application_id': str(self.application.id), 'configuration_id': str(self.configuration.id),
            'org_id': str(self.org.id), 'nonce': f'{self.configuration.id}-{nonce}',
        }, salt='credential-agent-register')
        request = self.factory.post('/api/v1/accounts/credential-client/register-agent/', {
            'token': token, 'instance_id': instance,
        }, format='json')
        with transaction.atomic():
            return CredentialClientViewSet.as_view(
                {'post': 'register_agent'}, authentication_classes=[], permission_classes=[AllowAny],
            )(request)

    def test_new_token_cannot_replace_existing_identity_or_reenable_it(self):
        first = self.register('one')
        self.assertEqual(first.status_code, 201)
        client = CredentialClientInstance.objects.get(pk=first.data['agent_id'])
        original = client.secret
        for enabled in (True, False):
            client.is_active = enabled
            client.save()
            response = self.register(f'two-{enabled}')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data['code'], 'client_instance_exists')
            client.refresh_from_db()
            self.assertEqual(client.secret, original)
            self.assertEqual(client.is_active, enabled)

    def test_used_token_cannot_create_another_instance(self):
        self.assertEqual(self.register('one').status_code, 201)
        response = self.register('one', 'other')
        self.assertEqual(response.data['code'], 'registration_token_used')
        self.assertEqual(CredentialClientInstance.objects.filter(configuration=self.configuration).count(), 1)


class AgentInstallTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.args = SimpleNamespace(
            endpoint='http://localhost', token='token', instance_id='agent', name=None,
            config=str(root / 'agent.json'), credential_file=str(root / 'credentials.json'),
            state_file=str(root / 'state.json'), app_user=pwd.getpwuid(os.getuid()).pw_name, port=8081,
        )
        self.identity = {'org_id': 'org', 'agent_id': 'id', 'agent_secret': 'test-secret',
                         'credential_keys': [], 'configuration_id': 'configuration'}

    def first_install(self):
        response = Mock()
        response.json.return_value = self.identity
        with patch('accounts.demos.python.jms_pam.agent.requests.post', return_value=response):
            return register(self.args)

    def test_reinstall_reuses_identity_without_registration_or_clearing_state(self):
        original = self.first_install()
        atomic_write_json(self.args.state_file, {'key': {'revision': 2}})
        with patch('accounts.demos.python.jms_pam.agent.requests.post') as post, \
                patch('accounts.demos.python.jms_pam.agent.Agent') as agent:
            self.assertEqual(register(self.args), original)
            post.assert_not_called()
            agent.return_value.heartbeat.assert_called_once()
        self.assertEqual(read_json(self.args.state_file), {'key': {'revision': 2}})

    def test_mismatched_install_does_not_overwrite_local_identity(self):
        original = self.first_install()
        self.args.instance_id = 'other'
        with patch('accounts.demos.python.jms_pam.agent.requests.post') as post:
            with self.assertRaises(ValueError):
                register(self.args)
            post.assert_not_called()
        self.assertEqual(read_json(self.args.config), original)

    def test_lost_response_and_failed_local_save_explain_recovery(self):
        with patch('accounts.demos.python.jms_pam.agent.requests.post', side_effect=requests.Timeout()):
            with self.assertRaisesRegex(RuntimeError, 'Check whether the instance was created'):
                register(self.args)
        response = Mock()
        response.json.return_value = self.identity
        with patch('accounts.demos.python.jms_pam.agent.requests.post', return_value=response), \
                patch('accounts.demos.python.jms_pam.agent.atomic_write_json', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(RuntimeError, 'identity could not be saved'):
                register(self.args)

    def test_failed_identity_check_preserves_configuration(self):
        original = self.first_install()
        with patch('accounts.demos.python.jms_pam.agent.Agent') as agent:
            agent.return_value.heartbeat.side_effect = requests.HTTPError()
            with self.assertRaisesRegex(RuntimeError, 'Configuration was preserved'):
                register(self.args)
        self.assertEqual(read_json(self.args.config), original)

    def test_install_restarts_and_checks_service(self):
        with patch('accounts.demos.python.jms_pam.agent.register'), \
                patch('accounts.demos.python.jms_pam.agent.shutil.which', return_value='/usr/bin/jms-pam-agent'), \
                patch('accounts.demos.python.jms_pam.agent.Path.write_text'), \
                patch('accounts.demos.python.jms_pam.agent.subprocess.run') as run:
            install(self.args)
        self.assertEqual([call.args[0] for call in run.call_args_list], [
            ['systemctl', 'daemon-reload'], ['systemctl', 'enable', 'jms-pam-agent'],
            ['systemctl', 'restart', 'jms-pam-agent'], ['systemctl', 'is-active', '--quiet', 'jms-pam-agent'],
        ])

    def test_sdk_requires_explicit_stable_instance_id(self):
        with patch.dict(os.environ, {}, clear=True):
            for value in (None, '', ' ', ' worker ', 'a' * 129):
                with self.assertRaisesRegex(ValueError, 'stable, unique ID'):
                    JumpServerPAMClient('http://localhost', 'id', 'secret', instance_id=value)
            first = JumpServerPAMClient('http://localhost', 'id', 'secret', instance_id='orders-worker-1')
            second = JumpServerPAMClient('http://localhost', 'id', 'secret', instance_id='orders-worker-2')
            self.assertNotEqual(first.http.instance_id, second.http.instance_id)
            first.close()
            second.close()
        with patch.dict(os.environ, {'JMS_PAM_INSTANCE_ID': 'orders-worker-3'}):
            client = JumpServerPAMClient('http://localhost', 'id', 'secret')
            self.assertEqual(client.instance_id, 'orders-worker-3')
            client.close()


class AgentDeliveryTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.target = root / 'application.env'
        self.rule = {
            'format': 'env', 'path': str(self.target),
            'fields': {'DB_USER': 'username', 'DB_PASSWORD': 'secret'},
            'owner': pwd.getpwuid(os.getuid()).pw_name, 'mode': '0600',
            'apply': ['/usr/local/sbin/apply-test-application'],
            'confirmation': 'apply', 'timeout': 30,
        }
        self.agent = Agent.__new__(Agent)
        self.agent.config = {
            'credential_keys': ['db'], 'app_user': self.rule['owner'],
            'credential_file': str(root / 'credentials.json'),
            'state_file': str(root / 'state.json'),
            'delivery_state_file': str(root / 'delivery-state.json'),
            'deliveries': {'db': self.rule},
        }
        self.agent.credentials = {
            'db': {
                'key': 'db', 'revision': 2, 'asset_id': 'asset', 'address': '127.0.0.1',
                'account_id': 'account-2', 'username': 'app_b', 'secret_type': 'password',
                'secret': "new secret's value",
            }
        }
        self.agent.state = {}
        self.agent.delivery_state = {}
        self.agent.lock = threading.Lock()
        self.agent.delivery_lock = threading.Lock()
        self.agent.remote = Mock()

    @patch('accounts.demos.python.jms_pam.agent.run_hook')
    def test_apply_writes_env_and_confirms_exact_revision(self, hook):
        self.agent.deliver('db')
        self.assertEqual(
            self.target.read_text(),
            "DB_USER=app_b\nDB_PASSWORD='new secret'\"'\"'s value'\n",
        )
        hook.assert_called_once_with(self.rule, 'published', 'db', 2)
        self.agent.remote.confirm.assert_called_once_with({
            'key': 'db', 'revision': 2, 'account_id': 'account-2',
        })
        self.assertEqual(self.agent.delivery_state['db']['status'], 'applied')
        self.assertEqual(self.agent.state['db']['revision'], 2)

    @patch('accounts.demos.python.jms_pam.agent.run_hook')
    def test_failed_apply_retries_same_revision_without_confirming_early(self, hook):
        hook.side_effect = [RuntimeError('failed'), None]
        with patch('sys.stderr'):
            self.agent.deliver('db')
        self.assertEqual(self.agent.delivery_state['db']['status'], 'pending')
        self.agent.remote.confirm.assert_not_called()

        self.agent.deliver('db')
        self.assertEqual(hook.call_count, 2)
        self.agent.remote.confirm.assert_called_once()

    @patch('accounts.demos.python.jms_pam.agent.run_hook')
    def test_confirmation_retry_does_not_run_apply_again(self, hook):
        self.agent.remote.confirm.side_effect = [requests.Timeout(), None]
        with patch('sys.stderr'):
            self.agent.deliver('db')
        self.agent.deliver('db')
        hook.assert_called_once()
        self.assertEqual(self.agent.remote.confirm.call_count, 2)
        self.assertEqual(self.agent.state['db']['revision'], 2)

    @patch('accounts.demos.python.jms_pam.agent.run_hook')
    def test_new_revision_during_apply_prevents_old_confirmation(self, hook):
        calls = 0

        def publish_new_revision(*_):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.agent.credentials['db'] = {
                    **self.agent.credentials['db'],
                    'revision': 3, 'account_id': 'account-3', 'username': 'app_a', 'secret': 'newer',
                }

        hook.side_effect = publish_new_revision
        self.agent.deliver('db')
        self.agent.remote.confirm.assert_not_called()

        self.agent.deliver('db')
        self.agent.remote.confirm.assert_called_once_with({
            'key': 'db', 'revision': 3, 'account_id': 'account-3',
        })

    @patch('accounts.demos.python.jms_pam.agent.run_hook')
    def test_revocation_deletes_delivery_and_retries_failed_hook(self, hook):
        self.target.write_text('DB_PASSWORD=old\n')
        self.agent.state['db'] = {'key': 'db', 'revision': 2, 'account_id': 'account-2'}
        sent_credentials, sent_state = dict(self.agent.credentials), dict(self.agent.state)
        with self.agent.lock:
            self.agent.remove_revoked({'db'}, sent_credentials, sent_state)
        # A crash can leave the older raw cache on disk after the revoke tombstone was saved.
        self.agent.credentials['db'] = sent_credentials['db']
        self.agent.state['db'] = sent_state['db']

        hook.side_effect = [RuntimeError('failed'), None]
        with patch('sys.stderr'):
            self.agent.reconcile_deliveries({'db'})
        self.assertFalse(self.target.exists())
        self.assertEqual(self.agent.delivery_state['db']['status'], 'pending')

        self.agent.reconcile_deliveries({'db'})
        self.assertEqual(hook.call_count, 2)
        self.assertEqual(hook.call_args.args[1], 'revoked')
        self.assertEqual(self.agent.delivery_state['db']['status'], 'applied')
        self.assertNotIn('db', self.agent.credentials)
        self.assertNotIn('db', self.agent.state)

    @patch('accounts.demos.python.jms_pam.agent.run_hook')
    def test_manual_delivery_never_confirms_automatically(self, hook):
        self.rule['confirmation'] = 'manual'
        self.agent.deliver('db')
        hook.assert_called_once()
        self.agent.remote.confirm.assert_not_called()

    @patch('accounts.demos.python.jms_pam.agent.run_hook')
    def test_delivery_refuses_to_replace_symlink(self, hook):
        victim = self.target.with_name('victim.env')
        victim.write_text('keep-me\n')
        self.target.symlink_to(victim)

        with patch('sys.stderr'):
            self.agent.deliver('db')

        self.assertEqual(victim.read_text(), 'keep-me\n')
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(self.agent.delivery_state['db']['error'], 'ValueError')
        hook.assert_not_called()
        self.agent.remote.confirm.assert_not_called()
