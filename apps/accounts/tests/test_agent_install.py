from accounts.credential_client.manager import CredentialClientManager
from accounts.models import (
    Account, ApplicationCredential, CredentialApplicationBinding,
    CredentialClientInstance, CredentialClientStatus,
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

    def test_account_rule_scope_exposes_switch_group_and_excludes_other_rotation(self):
        third = Account.objects.create(name='third', username='third', asset=self.asset, secret='third-secret')
        fourth = Account.objects.create(name='fourth', username='fourth', asset=self.asset, secret='fourth-secret')
        self.application.accounts = {
            'type': 'ids', 'ids': [str(value.id) for value in (self.primary, self.backup, third, fourth)],
        }
        self.application.save()
        other = ApplicationCredential.objects.create(
            name='Other database', mode='alternating_rotation', account=third,
            alternate_account=fourth, active_account=third,
        )
        CredentialApplicationBinding.objects.create(credential=other, application=self.application)
        manager = CredentialClientManager(self.client)
        scope = {'keys': [], 'account_ids': [str(self.primary.id)]}
        result = manager.sync_agent(delivery_scope=scope)
        self.assertEqual(result['scope']['credential_keys'], [self.credential.key])
        self.assertEqual(result['credentials'][0]['account_switch'], self.credential.account_switch)
        self.client.refresh_from_db()
        self.assertEqual(self.client.delivery_scope, scope)
        fetched = manager.fetch(self.credential.key, '127.0.0.1')
        self.assertEqual(fetched['account_switch'], self.credential.account_switch)
        accounts = manager.authorized_accounts()['accounts']
        active = next(item for item in accounts if item['id'] == str(self.primary.id))
        self.assertEqual(active['credentials'][0]['account_switch'], self.credential.account_switch)
        from accounts.credential_rotation.manager import CredentialRotationManager
        CredentialRotationManager(other.id)._publish(other)
        self.assertFalse(CredentialClientStatus.objects.filter(
            client=self.client, binding__credential=other, is_rotation_participant=True,
        ).exists())
        CredentialRotationManager(self.credential.id)._publish(self.credential)
        self.assertTrue(CredentialClientStatus.objects.filter(
            client=self.client, binding__credential=self.credential, is_rotation_participant=True,
        ).exists())
        with self.assertRaises(Exception):
            manager.sync_agent(delivery_scope={'keys': [], 'account_ids': [str(third.id)]})

    def test_unsynchronized_agent_does_not_join_rotation_before_declaring_accounts(self):
        from accounts.credential_rotation.manager import CredentialRotationManager
        CredentialRotationManager(self.credential.id)._publish(self.credential)
        self.assertFalse(CredentialClientStatus.objects.filter(
            client=self.client, binding__credential=self.credential, is_rotation_participant=True,
        ).exists())
