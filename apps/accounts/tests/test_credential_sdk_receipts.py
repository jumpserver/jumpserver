import json
from unittest import TestCase
from unittest.mock import Mock, patch

import websocket

from accounts.demos.python.jms_pam.common.credential import Credential
from accounts.demos.python.jms_pam.common.profile.client_profile import ClientProfile
from accounts.demos.python.jms_pam.credential.v1 import credential_client


class CredentialSDKReceiptTests(TestCase):
    def setUp(self):
        self.client = credential_client.CredentialClient(
            Credential('application', 'test-secret'), 'instance',
            ClientProfile(endpoint='https://testserver', configuration_id='configuration'),
        )
        self.addCleanup(self.client.close)

    def read_event(self, event, send_error=None):
        connection = Mock()
        connection.recv.return_value = json.dumps(event)
        connection.send.side_effect = send_error
        with patch.object(credential_client.websocket, 'create_connection', return_value=connection):
            stream = self.client.WatchCredentialEvents()
            try:
                self.assertEqual(next(stream), event)
            finally:
                stream.close()
        connection.close.assert_called_once()
        return connection

    def test_business_events_are_acknowledged_before_yield(self):
        for code in (
            'credential.updated', 'credential.revoked', 'configuration.updated',
            'credential.change.started', 'credential.change.completed', 'credential.change.failed',
            'rotation.started', 'rotation.waiting_for_application', 'rotation.completed',
        ):
            with self.subTest(event=code):
                connection = self.read_event({'event': code, 'event_id': 'event-id'})
                connection.send.assert_called_once()
                self.assertEqual(json.loads(connection.send.call_args.args[0]), {
                    'event': 'received', 'event_id': 'event-id',
                })

    def test_receipt_failure_does_not_hide_event(self):
        for error in (OSError('disconnected'), websocket.WebSocketException('send failed')):
            with self.subTest(error=type(error).__name__):
                connection = self.read_event(
                    {'event': 'credential.updated', 'event_id': 'event-id'}, send_error=error,
                )
                connection.send.assert_called_once()

    def test_snapshot_pong_and_legacy_events_do_not_send_receipts(self):
        for event in (
            {'event': 'snapshot', 'event_id': 'snapshot-id', 'credentials': []},
            {'event': 'credential.updated'},
        ):
            with self.subTest(event=event['event']):
                self.read_event(event).send.assert_not_called()

    def test_idle_connection_uses_application_heartbeat(self):
        connection = Mock()
        connection.recv.side_effect = [
            websocket.WebSocketTimeoutException(),
            json.dumps({'event': 'pong'}),
            json.dumps({'event': 'credential.updated', 'event_id': 'event-id'}),
        ]
        with patch.object(credential_client.websocket, 'create_connection', return_value=connection):
            stream = self.client.WatchCredentialEvents()
            try:
                self.assertEqual(next(stream)['event'], 'credential.updated')
            finally:
                stream.close()
        self.assertEqual(json.loads(connection.send.call_args_list[0].args[0]), {'event': 'ping'})
        self.assertEqual(json.loads(connection.send.call_args_list[1].args[0]), {
            'event': 'received', 'event_id': 'event-id',
        })

    def test_sdk_and_agent_advertise_receipt_support(self):
        for source in ('jms-pam', 'jms-pam-agent'):
            with self.subTest(source=source):
                self.client.profile.Source = source
                self.assertIn('X-JMS-Event-Receipts: 1', self.client._event_stream_headers())
