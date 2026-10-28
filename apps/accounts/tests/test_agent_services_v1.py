from uuid import uuid4
from unittest.mock import patch, PropertyMock

from django.utils import timezone

from accounts.credential_client.event_results import report
from accounts.credential_client.manager import CredentialClientManager, client_uses_credential
from accounts.models import Account, ApplicationAudit, ApplicationCredential, CredentialClientInstance, CredentialClientStatus
from accounts.tests.base import CredentialTestCase
from accounts.tests.test_application_access import ApplicationAccessTests


class AgentServicesV1Tests(CredentialTestCase):
    signed_request = ApplicationAccessTests.signed_request

    def sync(self, *, accounts=(), switching=(), all_accounts=False, instance='services-v1', **extra):
        response = self.signed_request('sync_agent', {
            'instance_id': instance,
            'delivery_scope': {'keys': [], 'account_ids': list(accounts), 'include_authorized': True,
                               'all_authorized': all_accounts, 'switch_account_ids': list(switching)},
            **extra,
        }, source='jms-pam-agent')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['config_schema_version'], 1)
        self.assertIn('agent_store_services', response.data['server_capabilities'])
        return response.data

    def test_all_authorized_storage_does_not_require_push_or_join_rotation(self):
        self.application.credential_bindings.all().delete()
        result = self.sync(all_accounts=True)
        self.assertEqual(set(result['scope']['credential_keys']), {
            f'account:{self.primary.id}', f'account:{self.backup.id}',
        })
        self.assertEqual(result['scope']['confirmation_keys'], [])
        self.assertFalse(CredentialClientStatus.objects.exists())
        self.assertFalse(ApplicationAudit.objects.filter(event='credential_fetched').exists())
        self.assertNotIn('secret', str(result))
        self.assertTrue(all(item['available'] for item in result['credentials']))

    def test_fixed_account_and_switching_service_have_independent_scopes(self):
        fixed = self.sync(accounts=[str(self.primary.id)])
        self.assertEqual(fixed['scope']['credential_keys'], [f'account:{self.primary.id}'])
        client = CredentialClientInstance.objects.get(instance_id='services-v1')
        self.assertFalse(client_uses_credential(client, self.credential))
        switched = self.sync(switching=[str(self.primary.id)])
        self.assertEqual(switched['scope']['confirmation_keys'], [self.credential.key])
        item = switched['credentials'][0]
        self.assertEqual(item['account_id'], str(self.primary.id))
        self.assertEqual(item['account_switch'], self.credential.account_switch)
        client.refresh_from_db()
        self.assertTrue(client_uses_credential(client, self.credential))
        report(client, item['event_id'])
        self.assertEqual(CredentialClientStatus.objects.get(client=client).applied_revision, self.credential.revision)

    def test_unknown_switch_account_is_not_authorized_and_unassociated_account_is_fixed(self):
        third = Account.objects.create(name='third', username='third', asset=self.asset, secret='third-secret')
        self.application.accounts = {'type': 'ids', 'ids': [str(third.id)]}
        self.application.save()
        unknown = str(uuid4())
        result = self.sync(switching=[str(third.id), unknown])
        self.assertEqual(result['scope']['credential_keys'], [f'account:{third.id}'])
        self.assertEqual(result['scope']['confirmation_keys'], [])
        self.assertEqual(result['unavailable_switch_account_ids'], [unknown])

    def test_unbound_unauthorized_and_ambiguous_switches_never_fall_back(self):
        for change in ('unbound', 'unauthorized', 'ambiguous'):
            with self.subTest(change=change):
                if change == 'unbound':
                    self.credential.applications.remove(self.application)
                elif change == 'unauthorized':
                    self.credential.applications.add(self.application)
                    self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
                    self.application.save()
                else:
                    self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id), str(self.backup.id)]}
                    self.application.save()
                    duplicate = ApplicationCredential.objects.create(
                        name='ambiguous', mode='alternating_rotation', account=self.primary,
                        alternate_account=self.backup, active_account=self.primary,
                    )
                    duplicate.applications.add(self.application)
                result = self.sync(switching=[str(self.primary.id)])
                self.assertEqual(result['credentials'], [])
                self.assertEqual(result['unavailable_switch_account_ids'], [str(self.primary.id)])
                client = CredentialClientInstance.objects.get(instance_id='services-v1')
                self.assertFalse(client_uses_credential(client, self.credential))

    def test_storage_cannot_confirm_rotation_and_standby_is_unavailable_during_change(self):
        ApplicationCredential.objects.filter(pk=self.credential.pk).update(
            status='changing_secret', date_rotation_started=timezone.now(),
        )
        result = self.sync(all_accounts=True)
        items = {item['account_id']: item for item in result['credentials']}
        self.assertTrue(items[str(self.primary.id)]['available'])
        self.assertFalse(items[str(self.backup.id)]['available'])
        self.assertEqual(result['scope']['confirmation_keys'], [])
        self.assertFalse(CredentialClientStatus.objects.exists())

    def test_revocation_and_empty_declarations_remove_previous_keys(self):
        result = self.sync(all_accounts=True)
        known = [{'key': item['key'], 'revision': item['revision']} for item in result['credentials']]
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save()
        revoked = self.sync(all_accounts=True, credentials=known)
        self.assertEqual(revoked['removed_keys'], [f'account:{self.backup.id}'])
        empty = self.sync(credentials=known)
        self.assertEqual(empty['credentials'], [])
        self.assertEqual(set(empty['removed_keys']), {item['key'] for item in known})

    def test_scope_validation_requires_v1_account_selectors(self):
        for scope in (
            {'keys': [], 'account_ids': [], 'all_authorized': True},
            {'keys': [], 'account_ids': [], 'switch_account_ids': [str(self.primary.id)]},
            {'keys': [], 'account_ids': [], 'include_authorized': True,
             'switch_account_ids': [str(self.primary.id)] * 2},
            {'keys': [self.credential.key], 'account_ids': [], 'include_authorized': True},
        ):
            response = self.signed_request('sync_agent', {
                'instance_id': 'invalid-service', 'delivery_scope': scope,
            }, source='jms-pam-agent')
            self.assertEqual(response.status_code, 400, response.data)

    def test_missing_password_is_unavailable_without_fetching_vault_secrets(self):
        Account.objects.filter(pk=self.backup.pk).update(_secret=None)
        with patch.object(Account, 'secret', new_callable=PropertyMock, side_effect=AssertionError('metadata fetched a secret')):
            result = self.sync(all_accounts=True)
        items = {item['account_id']: item for item in result['credentials']}
        self.assertTrue(items[str(self.primary.id)]['available'])
        self.assertFalse(items[str(self.backup.id)]['available'])
        self.assertFalse(ApplicationAudit.objects.filter(event='credential_fetched').exists())
