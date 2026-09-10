import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from django.db import transaction
from django.test import SimpleTestCase
from rest_framework.test import force_authenticate

from accounts.api.account.credential import CredentialClientViewSet
from accounts.credential_client.manager import CredentialClientManager
from accounts.demos.python.jms_pam.agent import Agent, read_json
from accounts.demos.python.jms_pam.main import JumpServerPAMClient
from accounts.models import ClientAccessConfiguration, CredentialClientStatus
from accounts.tests.base import CredentialTestCase


def http_error(code, status=403):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps({'code': code, 'detail': 'DO_NOT_LOG_SECRET'}).encode()
    return requests.HTTPError(response=response)


class ClientIsolationTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.agent = Agent.__new__(Agent)
        self.agent.config = {
            'credential_keys': ['a', 'b', 'c'],
            'credential_file': str(Path(directory.name) / 'credentials.json'),
            'state_file': str(Path(directory.name) / 'state.json'),
        }
        self.agent.lock = threading.Lock()
        self.agent.credentials = {key: {'revision': 1, 'secret': 'old'} for key in 'abc'}
        self.agent.state = {key: {'key': key, 'revision': 1, 'account_id': key} for key in 'abc'}
        self.agent.remote = Mock()

    @staticmethod
    def fetched(key):
        return {'key': key, 'revision': 2,
                'asset': {'id': 'asset', 'name': 'asset', 'address': '127.0.0.1'},
                'account': {'id': key, 'name': key, 'username': key, 'secret_type': 'password', 'secret': 'new'}}

    def test_partial_fetch_revokes_one_and_writes_other_results(self):
        self.agent.remote.get_credential.side_effect = [self.fetched('a'), http_error('credential_not_selected'), self.fetched('c')]
        with patch('sys.stderr') as stderr:
            errors = self.agent.poll()
        self.assertEqual(errors, {'b': 'credential_not_selected'})
        self.assertNotIn('DO_NOT_LOG_SECRET', str(stderr.write.call_args_list))
        persisted = read_json(self.agent.credential_file)
        self.assertEqual(set(persisted), {'a', 'c'})
        self.assertEqual(persisted['a']['revision'], 2)
        self.assertEqual(persisted['c']['revision'], 2)
        self.assertNotIn('b', read_json(self.agent.state_file))
        self.assertEqual(self.agent.state['a']['revision'], 1)

    def test_temporary_failures_preserve_only_failed_item(self):
        for error in (requests.Timeout(), http_error('credential_changing', 400), http_error('credential_not_found', 500)):
            with self.subTest(error=type(error).__name__):
                self.agent.remote.get_credential.side_effect = [self.fetched('a'), error, self.fetched('c')]
                self.agent.poll()
                self.assertEqual(self.agent.credentials['b']['revision'], 1)
                self.assertEqual(self.agent.credentials['c']['revision'], 2)

    def test_identity_failure_does_not_commit_partial_batch(self):
        for status, code in ((401, 'authentication_failed'), (403, 'client_disabled'), (403, 'configuration_disabled')):
            with self.subTest(code=code):
                self.agent.remote.get_credential.reset_mock()
                self.agent.remote.get_credential.side_effect = [self.fetched('a'), http_error(code, status), self.fetched('c')]
                with self.assertRaises(requests.HTTPError):
                    self.agent.poll()
                self.assertEqual(self.agent.credentials['a']['revision'], 1)
                self.assertEqual(self.agent.remote.get_credential.call_count, 2)

    def test_heartbeat_cleanup_and_late_response(self):
        reply = {'updated': ['a'], 'errors': [{'key': 'b', 'code': 'credential_not_authorized'}]}
        self.agent.remote.heartbeat.return_value = reply
        self.agent.heartbeat()
        self.assertNotIn('b', self.agent.credentials)
        self.assertNotIn('b', self.agent.state)
        self.agent.credentials['b'] = {'revision': 2}
        self.agent.state['b'] = {'revision': 2}

        def concurrent_confirmation(_):
            # Even a new confirmation of the same revision must survive an old response.
            self.agent.state['b'] = dict(self.agent.state['b'])
            return reply

        self.agent.remote.heartbeat.side_effect = concurrent_confirmation
        self.agent.heartbeat()
        self.assertIn('b', self.agent.credentials)
        self.assertIn('b', self.agent.state)

    def test_sdk_partial_heartbeat_preserves_new_confirmation(self):
        sdk = JumpServerPAMClient('http://localhost', 'id', 'secret', instance_id='isolation-test')
        self.addCleanup(sdk.close)
        sdk._applied = {'a': {'revision': 1}, 'b': {'revision': 1}}
        reply = {'updated': [], 'errors': [{'key': 'a', 'code': 'credential_revision_mismatch'},
                                         {'key': 'b', 'code': 'credential_not_selected'}]}
        sdk.http.heartbeat = Mock(return_value=reply)
        sdk.heartbeat()
        self.assertEqual(set(sdk._applied), {'a'})
        sdk._applied['b'] = {'revision': 2}
        def new_confirmation(_):
            sdk._applied['b'] = dict(sdk._applied['b'])
            return reply
        sdk.http.heartbeat.side_effect = new_confirmation
        sdk.heartbeat()
        self.assertIn('b', sdk._applied)

    def test_late_fetch_rejection_preserves_new_confirmation(self):
        def denied_after_confirmation(key):
            self.agent.state[key] = dict(self.agent.state[key])
            raise http_error('credential_not_selected')
        self.agent.remote.get_credential.side_effect = denied_after_confirmation
        self.agent.poll(keys=['b'])
        self.assertIn('b', self.agent.credentials)
        self.assertIn('b', self.agent.state)

    def test_late_rejection_preserves_same_revision_refetch(self):
        current = self.fetched('b')
        current['revision'] = 1
        other_remote = Mock()
        other_remote.get_credential.return_value = current
        def old_rejection(key):
            self.agent.poll(keys=[key], remote=other_remote)
            raise http_error('credential_not_selected')
        self.agent.remote.get_credential.side_effect = old_rejection
        self.agent.poll(keys=['b'])
        self.assertIn('b', self.agent.credentials)
        self.assertIn('b', self.agent.state)

    def test_poll_failure_does_not_skip_heartbeat_or_stop_loop(self):
        for error, expected in ((OSError('disk full'), 1), (requests.Timeout(), 1), (http_error('client_disabled'), 0)):
            self.agent.start_local_server = Mock()
            self.agent.notification_session = Mock()
            self.agent.events = None
            self.agent.poll = Mock(side_effect=error)
            self.agent.heartbeat = Mock(return_value={})
            stop = Mock()
            stop.wait.side_effect = KeyboardInterrupt
            with patch('accounts.demos.python.jms_pam.agent.threading.Event', return_value=stop):
                self.agent.run()
            self.assertEqual(self.agent.heartbeat.call_count, expected)

    def test_notification_does_not_use_cached_revision_after_fetch_failure(self):
        from accounts.demos.python.jms_pam.events import DeliveryError
        self.agent.config['notification_url'] = 'http://localhost/events'
        self.agent.notification_session = Mock()
        self.agent.remote.get_credential.side_effect = requests.Timeout()
        with self.assertRaises(DeliveryError):
            self.agent.notify({'event': 'credential.published', 'key': 'a', 'revision': 1}, self.agent.remote)
        self.agent.notification_session.post.assert_not_called()


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
        }, format='json', HTTP_X_JMS_ORG=str(self.org.id))
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
        }, HTTP_X_JMS_ORG=str(self.org.id))
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
