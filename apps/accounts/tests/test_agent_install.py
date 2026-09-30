from accounts.credential_client.manager import CredentialClientManager
from accounts.models import (
    CredentialClientInstance,
    CredentialClientStatus,
)
from accounts.tests.base import CredentialTestCase


class AgentSyncTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.client = CredentialClientInstance.objects.create(
            application=self.application,
            type='agent', instance_id='orders-1', secret='secret',
        )

    def test_sync_returns_only_application_scope_and_never_local_delivery_settings(self):
        manager = CredentialClientManager(self.client)
        first = manager.sync_agent(
            credentials=[{'key': self.credential.key, 'revision': 0}],
            sync_status='', sync_error='',
        )
        self.assertNotIn('configuration', first)
        self.assertEqual(set(first['scope']), {'credential_keys', 'confirmation_keys'})
        self.assertTrue(first['credentials'][0]['changed'])

        second = manager.sync_agent(
            config_digest=first['config_digest'],
            credentials=[{'key': self.credential.key, 'revision': self.credential.revision}],
            sync_status='success', sync_error='',
        )
        self.assertNotIn('configuration', second)
        self.assertEqual(first['scope'], second['scope'])
        self.assertFalse(second['credentials'][0]['changed'])
        self.client.refresh_from_db()
        self.assertEqual(self.client.sync_status, 'success')

    def test_removed_credential_is_reported_without_client_delivery(self):
        manager = CredentialClientManager(self.client)
        self.credential.applications.remove(self.application)
        response = manager.sync_agent(
            credentials=[{'key': self.credential.key, 'revision': self.credential.revision}],
        )
        self.assertEqual(response['credentials'], [])
        self.assertEqual(response['removed_keys'], [self.credential.key])

    def test_delivery_report_does_not_confirm_application_use(self):
        manager = CredentialClientManager(self.client)
        fetched = manager.fetch(self.credential.key, '127.0.0.1')
        manager.sync_agent(delivered_credentials=[{
            'key': self.credential.key, 'revision': fetched['revision'],
        }])
        state = CredentialClientStatus.objects.get(client=self.client)
        self.assertEqual(state.delivered_revision, fetched['revision'])
        self.assertIsNotNone(state.date_delivered)
        self.assertEqual(state.applied_revision, 0)
