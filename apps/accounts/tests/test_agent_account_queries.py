from unittest.mock import patch

from accounts.credential_client.manager import CredentialClientManager
from accounts.models import (
    ApplicationCredential, CredentialApplicationBinding, CredentialClientStatus,
)
from accounts.tests.base import CredentialTestCase


class AgentAccountMetadataTests(CredentialTestCase):
    def test_list_includes_authorized_accounts_without_push_policy(self):
        self.application.credential_bindings.all().delete()
        manager = CredentialClientManager(self.application, instance_id='list')

        result = manager.authorized_accounts(limit=1, offset=0)

        self.assertEqual(result['count'], 2)
        self.assertEqual(len(result['accounts']), 1)
        self.assertEqual(result['accounts'][0]['credentials'], [])
        self.assertNotIn('secret', result['accounts'][0])

    def test_list_attaches_only_push_policies_to_matching_accounts(self):
        subscription = ApplicationCredential.objects.create(name='Subscribed', mode='subscription')
        subscription.subscription_accounts.add(self.primary)
        CredentialApplicationBinding.objects.create(
            credential=subscription, application=self.application,
        )
        manager = CredentialClientManager(self.application, instance_id='list')

        result = manager.authorized_accounts()

        by_id = {account['id']: account for account in result['accounts']}
        self.assertEqual(result['count'], 2)
        self.assertIn(
            {'key': subscription.account_key(self.primary.id), 'mode': 'subscription',
             'revision': self.primary.version},
            by_id[str(self.primary.id)]['credentials'],
        )
        self.assertEqual(by_id[str(self.backup.id)]['credentials'], [])

    def test_overlapping_subscriptions_share_account_key_until_last_policy_removed(self):
        first = ApplicationCredential.objects.create(name='First push', mode='subscription')
        second = ApplicationCredential.objects.create(name='Second push', mode='subscription')
        for policy in (first, second):
            policy.subscription_accounts.add(self.primary)
            CredentialApplicationBinding.objects.create(
                credential=policy, application=self.application,
            )
        manager = CredentialClientManager(self.application, instance_id='overlap', client_type='agent')
        key = f'account:{self.primary.id}'

        self.assertEqual(CredentialClientManager.credential_keys(manager.application), [key, self.credential.key])
        by_id = {item['id']: item for item in manager.authorized_accounts()['accounts']}
        self.assertEqual(
            [item for item in by_id[str(self.primary.id)]['credentials'] if item['mode'] == 'subscription'],
            [{'key': key, 'mode': 'subscription', 'revision': self.primary.version}],
        )
        self.assertEqual(manager.fetch(key, '127.0.0.1')['account']['secret'], self.primary.secret)
        manager.sync_agent(delivered_credentials=[{'key': key, 'revision': self.primary.version}])
        delivered = CredentialClientStatus.objects.filter(
            binding__credential__in=(first, second), client=manager.client,
        ).values_list('delivered_revision', flat=True)
        self.assertEqual(list(delivered), [self.primary.version, self.primary.version])

        self.application.credential_bindings.filter(credential=first).delete()
        self.assertIn(key, CredentialClientManager.credential_keys(manager.application))
        self.assertEqual(manager.fetch(key, '127.0.0.1')['key'], key)

        self.application.credential_bindings.filter(credential=second).delete()
        self.assertNotIn(key, CredentialClientManager.credential_keys(manager.application))
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            manager.fetch(key, '127.0.0.1')
        self.assertEqual(manager.fetch('', '127.0.0.1', self.primary.id)['key'], key)

    def test_confirmation_keys_exclude_credentials_outside_application_authorization(self):
        with patch.object(CredentialClientManager, 'credential_keys', return_value=['subscription:account']), \
                patch.object(CredentialClientManager, 'confirmation_keys', return_value=['revoked-rotation']):
            scope = CredentialClientManager.agent_configuration(object())
        self.assertEqual(scope, {'credential_keys': ['subscription:account'], 'confirmation_keys': []})
