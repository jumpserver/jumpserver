import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch

from django.db import transaction
from django.test import SimpleTestCase
from rest_framework.test import force_authenticate

from accounts.api.account.credential import CredentialClientViewSet
from accounts.credential_client.manager import CredentialClientManager
from accounts.demos.python.jms_pam.agent import Agent, read_json
from accounts.demos.python.jms_pam.common.exception import JumpServerPAMSDKException
from accounts.demos.python.jms_pam.credential.v1 import models
from accounts.models import ClientAccessConfiguration, CredentialClientStatus
from accounts.tests.base import CredentialTestCase


def http_error(code, status=403):
    return JumpServerPAMSDKException(
        code, 'request failed', status_code=status, detail='DO_NOT_LOG_SECRET',
    )


class ClientIsolationTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.agent = Agent.__new__(Agent)
        self.agent.config = {
            'credential_file': str(Path(directory.name) / 'credentials.json'),
            'state_file': str(Path(directory.name) / 'state.json'),
        }
        self.agent.config_file = str(Path(directory.name) / 'agent.json')
        self.agent.lock = threading.Lock()
        self.agent.credentials = {
            key: {'key': key, 'revision': 1, 'account_id': key, 'secret': 'old'}
            for key in 'abc'
        }
        self.agent.state = {key: {'key': key, 'revision': 1, 'account_id': key} for key in 'abc'}
        self.agent.authorized_keys = set('abc')
        self.agent.access_denied = False
        self.agent.capabilities = {'socket_path': str(Path(directory.name) / 'agent.sock')}
        self.agent.remote = Mock()

    @staticmethod
    def fetched(key):
        return models.GetCredentialResponse()._deserialize({'key': key, 'revision': 2,
                'asset': {'id': 'asset', 'name': 'asset', 'address': '127.0.0.1'},
                'account': {'id': key, 'name': key, 'username': key, 'secret_type': 'password', 'secret': 'new'}})

    def test_partial_fetch_preserves_failed_item_and_writes_successes(self):
        self.agent.remote.GetCredential.side_effect = [self.fetched('a'), http_error('credential_not_selected'), self.fetched('c')]
        with patch('sys.stderr') as stderr:
            changed = self.agent.fetch(['a', 'b', 'c'])
        self.assertEqual(changed, {'a', 'c'})
        self.assertNotIn('DO_NOT_LOG_SECRET', str(stderr.write.call_args_list))
        persisted = read_json(self.agent.credential_file)
        self.assertEqual(set(persisted), {'a', 'b', 'c'})
        self.assertEqual(persisted['a']['revision'], 2)
        self.assertEqual(persisted['c']['revision'], 2)
        self.assertEqual(persisted['b']['revision'], 1)
        self.assertNotIn('b', self.agent.authorized_keys)

    def test_temporary_failures_preserve_only_failed_item(self):
        for error in (
            JumpServerPAMSDKException('NetworkError', 'slow'),
            http_error('credential_changing', 400), http_error('credential_not_found', 500),
        ):
            with self.subTest(error=type(error).__name__):
                self.agent.remote.GetCredential.side_effect = [self.fetched('a'), error, self.fetched('c')]
                self.agent.fetch(['a', 'b', 'c'])
                self.assertEqual(self.agent.credentials['b']['revision'], 1)
                self.assertEqual(self.agent.credentials['c']['revision'], 2)

    def test_identity_failure_does_not_commit_partial_batch(self):
        for status, code in ((401, 'authentication_failed'), (403, 'client_disabled'), (403, 'configuration_disabled')):
            with self.subTest(code=code):
                self.agent.remote.GetCredential.reset_mock()
                self.agent.remote.GetCredential.side_effect = [self.fetched('a'), http_error(code, status), self.fetched('c')]
                with self.assertRaises(JumpServerPAMSDKException):
                    self.agent.fetch(['a', 'b', 'c'])
                self.assertEqual(self.agent.credentials['a']['revision'], 1)
                self.assertEqual(self.agent.remote.GetCredential.call_count, 2)

    def test_heartbeat_reports_only_authorized_confirmations(self):
        reply = models.HeartbeatResponse()._deserialize({
            'updated': ['a'], 'errors': [],
            'date_last_seen': '2026-09-16T00:00:00Z',
        })
        self.agent.remote.Heartbeat.return_value = reply
        self.agent.authorized_keys = {'a'}
        self.agent.heartbeat()
        request = self.agent.remote.Heartbeat.call_args.args[0]._serialize()
        self.assertEqual([item['key'] for item in request['credentials']], ['a'])
        self.assertIn('b', self.agent.credentials)
        self.assertIn('b', self.agent.state)

    def test_sync_failure_does_not_skip_heartbeat_or_stop_loop(self):
        for error, expected in (
            (OSError('disk full'), 1),
            (JumpServerPAMSDKException('NetworkError', 'slow'), 1),
            (http_error('client_disabled'), 0),
        ):
            server = Mock()
            self.agent.start_local_server = Mock(return_value=server)
            self.agent.sync = Mock(side_effect=error)
            self.agent.heartbeat = Mock(return_value={})
            self.agent.set_access_denied = Mock(side_effect=lambda denied, reason='': setattr(self.agent, 'access_denied', denied))
            stop = Mock()
            stop.wait.side_effect = KeyboardInterrupt
            with patch('accounts.demos.python.jms_pam.agent.threading.Event', return_value=stop):
                self.agent.run()
            self.assertEqual(self.agent.heartbeat.call_count, expected)


class HeartbeatIsolationTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.configuration = ClientAccessConfiguration.objects.create(application=self.application, name='SDK', type='sdk')
        self.configuration.credentials.add(self.credential)
        self.manager = CredentialClientManager(self.application, self.configuration.id, 'instance')
        self.manager.fetch(self.credential.key, '127.0.0.1')

    def heartbeat(self, items):
        request = self.factory.post('/api/v1/accounts/credential-client/heartbeat/', {
            'configuration_id': str(self.configuration.id), 'instance_id': 'instance', 'credentials': items,
        }, format='json', HTTP_X_JMS_ORG=str(self.org.id),
            HTTP_X_JMS_CLIENT_VERSION='1.0.0', HTTP_X_JMS_PROTOCOL_VERSION='1',
            HTTP_X_JMS_CONFIG_SCHEMA_VERSION='0')
        force_authenticate(request, user=self.application)
        # Match ATOMIC_REQUESTS when calling a view directly with APIRequestFactory.
        with transaction.atomic():
            return CredentialClientViewSet.as_view({'post': 'heartbeat'})(request)

    def item(self, key=None, revision=1):
        return {'key': key or self.credential.key, 'revision': revision, 'account_id': str(self.primary.id)}

    def test_missing_credential_does_not_rollback_valid_confirmation(self):
        response = self.heartbeat([self.item('missing'), self.item()])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['updated'], [self.credential.key])
        self.assertEqual(response.data['errors'][0]['code'], 'credential_not_found')
        state = CredentialClientStatus.objects.get(client=self.manager.client)
        self.assertEqual(state.applied_revision, 1)

    def test_revocation_is_partial_but_disabled_identity_is_not(self):
        self.configuration.credentials.remove(self.credential)
        response = self.heartbeat([self.item()])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['errors'][0]['code'], 'credential_not_selected')
        self.configuration.is_active = False
        self.configuration.save()
        self.assertEqual(self.heartbeat([self.item()]).status_code, 403)

    def test_disabled_instance_and_application_reject_entire_heartbeat(self):
        self.manager.client.is_active = False
        self.manager.client.save()
        self.assertEqual(self.heartbeat([self.item()]).status_code, 403)
        self.manager.client.is_active = True
        self.manager.client.save()
        self.application.is_active = False
        self.application.save()
        self.assertIn(self.heartbeat([self.item()]).status_code, (401, 403))

    def test_fetch_rejection_has_machine_readable_code(self):
        request = self.factory.get('/api/v1/accounts/credential-client/credential/', {
            'configuration_id': str(self.configuration.id), 'instance_id': 'instance', 'key': 'missing',
        }, HTTP_X_JMS_ORG=str(self.org.id), HTTP_X_JMS_CLIENT_VERSION='1.0.0',
            HTTP_X_JMS_PROTOCOL_VERSION='1', HTTP_X_JMS_CONFIG_SCHEMA_VERSION='0')
        force_authenticate(request, user=self.application)
        response = CredentialClientViewSet.as_view({'get': 'credential'})(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'credential_not_found')

    def test_bad_revision_and_invalid_payload_are_not_confirmed(self):
        response = self.heartbeat([self.item(revision=2)])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['errors'][0]['code'], 'credential_revision_mismatch')
        state = CredentialClientStatus.objects.get(client=self.manager.client)
        self.assertNotEqual(state.applied_revision, 2)
        self.assertEqual(self.heartbeat([self.item(revision=0)]).status_code, 400)

    def test_unexpected_error_is_not_swallowed(self):
        with patch.object(self.manager, '_get_credential', side_effect=RuntimeError('database unavailable')):
            with self.assertRaises(RuntimeError):
                self.manager.heartbeat([self.item()])
