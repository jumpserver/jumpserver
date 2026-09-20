import json
import os
import pwd
import socket
import subprocess
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core import signing
from django.db import transaction
from django.test import SimpleTestCase
from rest_framework.permissions import AllowAny

from accounts.api.account.credential import CredentialClientViewSet
from accounts.credential_client.manager import CredentialClientManager
from accounts.demos.python.jms_pam.agent import Agent, install, read_json, register
from accounts.demos.python.jms_pam.common.credential import Credential as PAMCredential
from accounts.demos.python.jms_pam.common.profile.client_profile import ClientProfile
from accounts.demos.python.jms_pam.credential.v1.credential_client import CredentialClient
from accounts.demos.python.jms_pam.credential.v1 import models
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
            'application_id': str(self.application.id),
            'configuration_id': str(self.configuration.id),
            'org_id': str(self.org.id),
            'nonce': f'{self.configuration.id}-{nonce}',
        }, salt='credential-agent-register')
        request = self.factory.post('/api/v1/accounts/credential-client/register-agent/', {
            'token': token, 'instance_id': instance, 'client_version': '1.0.0',
            'protocol_version': 1, 'config_schema_version': 1,
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

    def test_unsupported_agent_protocol_requires_upgrade(self):
        response = self.register('version')
        self.assertEqual(response.status_code, 201)
        token = signing.dumps({
            'application_id': str(self.application.id),
            'configuration_id': str(self.configuration.id),
            'org_id': str(self.org.id), 'nonce': 'unsupported',
        }, salt='credential-agent-register')
        request = self.factory.post('/api/v1/accounts/credential-client/register-agent/', {
            'token': token, 'instance_id': 'new-agent', 'client_version': '2.0.0',
            'protocol_version': 2, 'config_schema_version': 1,
        }, format='json')
        response = CredentialClientViewSet.as_view(
            {'post': 'register_agent'}, authentication_classes=[], permission_classes=[AllowAny],
        )(request)
        self.assertEqual(response.status_code, 426)
        self.assertEqual(response.data['code'], 'client_upgrade_required')


class AgentInstallTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.user = pwd.getpwuid(os.getuid()).pw_name
        self.args = SimpleNamespace(
            endpoint='http://localhost', token='token', instance_id='agent', name=None,
            configuration_id='00000000-0000-0000-0000-000000000001',
            install_path=str(self.root), app_user=self.user,
            config=str(self.root / '00000000-0000-0000-0000-000000000001' / 'agent.json'),
        )
        configuration_id = self.args.configuration_id
        self.configuration = {
            'delivery_mode': 'json', 'credential_keys': [],
            'delivery_root': str(self.root / 'credentials' / configuration_id),
            'socket_path': str(self.root / 'run' / configuration_id / 'agent.sock'),
            'app_user': self.user, 'systemd_unit': '', 'systemd_action': 'restart',
        }
        self.identity = {
            'org_id': 'org', 'agent_id': 'id', 'agent_secret': 'test-secret',
            'credential_keys': [], 'configuration_id': configuration_id,
            'configuration': self.configuration, 'config_digest': 'digest',
        }

    def first_install(self):
        response = Mock()
        response.json.return_value = self.identity
        with patch('accounts.demos.python.jms_pam.agent.requests.post', return_value=response), \
                patch('accounts.demos.python.jms_pam.agent.secure_root', side_effect=lambda path, mode=0o711: Path(path)):
            return register(self.args)

    def test_registration_pins_server_capabilities(self):
        config_file = self.first_install()
        config = read_json(config_file)
        self.assertEqual(config['capabilities']['delivery_root'], self.configuration['delivery_root'])
        self.assertEqual(config['configuration'], self.configuration)

    def test_reinstall_reuses_identity_and_syncs(self):
        config_file = self.first_install()
        with patch('accounts.demos.python.jms_pam.agent.requests.post') as post, \
                patch('accounts.demos.python.jms_pam.agent.secure_root'), \
                patch('accounts.demos.python.jms_pam.agent.Agent') as agent:
            self.assertEqual(register(self.args), config_file)
            post.assert_not_called()
            agent.return_value.sync.assert_called_once()

    def test_install_uses_one_service_per_configuration(self):
        with patch('accounts.demos.python.jms_pam.agent.register', return_value=self.args.config), \
                patch('accounts.demos.python.jms_pam.agent.shutil.which', return_value='/usr/bin/jms-pam-agent'), \
                patch('accounts.demos.python.jms_pam.agent.atomic_write'), \
                patch('accounts.demos.python.jms_pam.agent.subprocess.run') as run:
            install(self.args)
        service = f'jms-pam-agent-{self.args.configuration_id}.service'
        self.assertEqual([call.args[0] for call in run.call_args_list], [
            ['systemctl', 'daemon-reload'],
            ['systemctl', 'enable', '--now', service],
            ['systemctl', 'is-active', '--quiet', service],
        ])

    def test_sdk_requires_explicit_stable_instance_id(self):
        cred = PAMCredential('id', 'secret')
        profile = ClientProfile(endpoint='http://localhost', configuration_id='config')
        for value in (None, '', ' ', ' worker ', 'a' * 129):
            with self.assertRaisesRegex(ValueError, 'stable, unique ID'):
                CredentialClient(cred, value, profile)
        CredentialClient(cred, 'orders-worker-1', profile).close()

    def test_client_version_headers_are_part_of_the_signature(self):
        expected = {
            'x-jms-client-version', 'x-jms-protocol-version',
            'x-jms-config-schema-version',
        }
        for authentication in CredentialClientViewSet.authentication_classes:
            self.assertTrue(expected.issubset(authentication.required_headers))

    def test_initial_agent_sync_allows_empty_status(self):
        request = models.AgentSyncRequest(
            ConfigDigest='', Credentials=[], SyncStatus='', SyncError='',
        )
        self.assertIs(request._validate(), request)


class AgentSyncTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Agent sync', type='agent',
            app_user='orders', delivery_mode='socket',
        )
        self.configuration.credentials.add(self.credential)
        self.client = CredentialClientInstance.objects.create(
            application=self.application, configuration=self.configuration,
            type='agent', instance_id='orders-1', secret='secret',
        )

    def test_sync_returns_configuration_only_when_digest_changes(self):
        manager = CredentialClientManager(self.client)
        first = manager.sync_agent(
            credentials=[{'key': self.credential.key, 'revision': 0}],
            sync_status='', sync_error='',
        )
        self.assertIn('configuration', first)
        self.assertTrue(first['credentials'][0]['changed'])

        second = manager.sync_agent(
            config_digest=first['config_digest'],
            credentials=[{'key': self.credential.key, 'revision': self.credential.revision}],
            sync_status='success', sync_error='',
        )
        self.assertNotIn('configuration', second)
        self.assertFalse(second['credentials'][0]['changed'])
        self.client.refresh_from_db()
        self.assertEqual(self.client.sync_status, 'success')

    def test_removed_credential_is_reported_without_client_delivery(self):
        manager = CredentialClientManager(self.client)
        self.configuration.credentials.remove(self.credential)
        response = manager.sync_agent(
            credentials=[{'key': self.credential.key, 'revision': self.credential.revision}],
        )
        self.assertEqual(response['credentials'], [])
        self.assertEqual(response['removed_keys'], [self.credential.key])


class AgentDeliveryTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.user = pwd.getpwuid(os.getuid()).pw_name
        self.agent = Agent.__new__(Agent)
        self.agent.configuration = {
            'delivery_mode': 'json', 'credential_keys': ['db'],
            'delivery_root': str(self.root), 'socket_path': str(self.root / 'agent.sock'),
            'app_user': self.user, 'systemd_unit': '', 'systemd_action': 'restart',
        }
        self.agent.capabilities = dict(self.agent.configuration)
        self.agent.credentials = {
            'db': {
                'key': 'db', 'revision': 2, 'asset_id': 'asset', 'asset': 'Database',
                'address': '127.0.0.1', 'account_id': 'account-2', 'account': 'app',
                'username': 'app_b', 'secret_type': 'password', 'secret': 'new-secret',
            }
        }
        self.agent.state = {}
        self.agent.authorized_keys = {'db'}
        self.agent.access_denied = False
        self.agent.lock = threading.Lock()
        self.agent.remote = Mock()
        self.agent.config_file = str(self.root / 'agent.json')
        self.agent.config = {
            'sync_status': '', 'sync_error': '',
            'state_file': str(self.root / 'state.json'),
        }

    def socket_request(self, request):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(self.agent.capabilities['socket_path'])
            client.sendall(request)
            response = b''
            while chunk := client.recv(65536):
                response += chunk
        headers, _, body = response.partition(b'\r\n\r\n')
        status = int(headers.split(b' ', 2)[1])
        return status, json.loads(body)

    def test_json_delivery_writes_one_file_without_confirming(self):
        with patch('accounts.demos.python.jms_pam.agent.secure_root', return_value=self.root):
            self.agent.deliver({'db'})
        self.assertEqual(read_json(self.root / 'db.json')['revision'], 2)
        self.agent.remote.ConfirmCredential.assert_not_called()

    def test_environment_delivery_runs_only_pinned_systemd_action(self):
        self.agent.configuration.update({
            'delivery_mode': 'environment', 'systemd_unit': 'orders.service',
            'systemd_action': 'reload',
        })
        with patch('accounts.demos.python.jms_pam.agent.secure_root', return_value=self.root), \
                patch('accounts.demos.python.jms_pam.agent.subprocess.run') as run:
            self.agent.deliver({'db'})
        self.assertIn('JMS_PAM_SECRET="new-secret"', (self.root / 'db.env').read_text())
        run.assert_called_once_with(
            ['systemctl', 'reload', 'orders.service'], check=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.agent.remote.ConfirmCredential.assert_not_called()

    def test_delivery_refuses_to_replace_symlink(self):
        victim = self.root / 'victim.json'
        victim.write_text('keep-me\n')
        (self.root / 'db.json').symlink_to(victim)
        with patch('accounts.demos.python.jms_pam.agent.secure_root', return_value=self.root):
            with self.assertRaises(ValueError):
                self.agent.deliver({'db'})
        self.assertEqual(victim.read_text(), 'keep-me\n')

    def test_unix_socket_serves_credentials_and_explicit_confirmation(self):
        with patch('accounts.demos.python.jms_pam.agent.secure_root', return_value=self.root), \
                patch('accounts.demos.python.jms_pam.agent.os.chown'), \
                patch('accounts.demos.python.jms_pam.agent.os.chmod'):
            server = self.agent.start_local_server()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        status, payload = self.socket_request(
            b'GET /v1/credentials/db HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n'
        )
        self.assertEqual((status, payload['secret']), (200, 'new-secret'))

        body = json.dumps({'key': 'db', 'revision': 2}).encode()
        request = (
            b'POST /v1/confirm HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n'
            + f'Content-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode() + body
        )
        status, payload = self.socket_request(request)
        self.assertEqual((status, payload['revision']), (200, 2))
        self.agent.remote.ConfirmCredential.assert_called_once()

        self.agent.access_denied = True
        status, payload = self.socket_request(
            b'GET /v1/credentials/db HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n'
        )
        self.assertEqual((status, payload['code']), (503, 'agent_access_denied'))
