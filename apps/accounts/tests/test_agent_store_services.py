import json

from accounts.credential_client.access import materials
from accounts.credential_client.manager import CredentialClientManager, scope_uses_credential
from accounts.models import Account, ApplicationCredential
from accounts.serializers.account.credential import CredentialAccessWizardSerializer, CredentialDeliveryScopeSerializer
from accounts.tests.base import CredentialTestCase


class AgentStoreServicesTests(CredentialTestCase):
    def scope(self, **values):
        serializer = CredentialDeliveryScopeSerializer(data={
            'keys': [], 'account_ids': [], 'include_authorized': True,
            **values,
        })
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def manager(self):
        return CredentialClientManager(self.application, instance_id='store-agent', client_type='agent')

    def test_all_authorized_synchronizes_without_subscriptions_or_rotation_enrollment(self):
        scope = self.scope(all_authorized=True)
        manager = self.manager()
        result = manager.sync_agent(delivery_scope=scope)
        self.assertEqual(result['config_schema_version'], 2)
        self.assertEqual(set(result['scope']['credential_keys']), {
            f'account:{self.primary.id}', f'account:{self.backup.id}',
        })
        self.assertEqual(result['scope']['confirmation_keys'], [])
        self.assertFalse(scope_uses_credential(scope, self.credential))
        self.assertFalse(ApplicationCredential.objects.filter(mode='subscription').exists())
        for item in result['credentials']:
            self.assertTrue(item['available'])
            self.assertEqual(item['event_id'], '')
        self.application.accounts = {'type': 'ids', 'ids': [str(self.backup.id)]}
        self.application.save()
        result = manager.sync_agent(delivery_scope=scope, credentials=[
            {'key': f'account:{self.primary.id}', 'revision': self.primary.version},
        ])
        self.assertEqual(result['scope']['credential_keys'], [f'account:{self.backup.id}'])
        self.assertEqual(result['removed_keys'], [f'account:{self.primary.id}'])

    def test_fixed_storage_and_switching_service_have_independent_scopes(self):
        scope = self.scope(account_ids=[str(self.primary.id)], switch_account_ids=[str(self.primary.id)])
        result = self.manager().sync_agent(delivery_scope=scope)
        self.assertEqual(set(result['scope']['credential_keys']), {f'account:{self.primary.id}', self.credential.key})
        self.assertEqual(result['scope']['confirmation_keys'], [self.credential.key])
        self.assertTrue(scope_uses_credential(scope, self.credential))

    def test_non_rotating_service_account_remains_fixed_when_switching_is_allowed(self):
        self.credential.is_active = False
        self.credential.save()
        scope = self.scope(switch_account_ids=[str(self.primary.id)])
        self.assertEqual(CredentialClientManager.credential_keys(self.application, scope), [f'account:{self.primary.id}'])

    def test_store_does_not_prefetch_inactive_account_while_password_changes(self):
        self.credential.status = 'changing_secret'
        self.credential.save()
        result = self.manager().sync_agent(delivery_scope=self.scope(all_authorized=True))
        items = {item['account_id']: item for item in result['credentials']}
        self.assertTrue(items[str(self.primary.id)]['available'])
        self.assertFalse(items[str(self.backup.id)]['available'])

    def test_missing_ab_authorization_blocks_switch_instead_of_falling_back(self):
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save()
        scope = self.scope(all_authorized=True, switch_account_ids=[str(self.primary.id)])
        result = self.manager().sync_agent(delivery_scope=scope)
        self.assertEqual(result['unavailable_switch_account_ids'], [str(self.primary.id)])
        self.assertEqual(result['scope']['credential_keys'], [f'account:{self.primary.id}'])
        self.assertEqual(result['scope']['confirmation_keys'], [])

    def test_wizard_builds_alias_mappings_and_service_level_options(self):
        cache = Account.objects.create(name='cache', username='cache', asset=self.asset, secret='cache-secret')
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id), str(self.backup.id), str(cache.id)]}
        self.application.save()
        serializer = CredentialAccessWizardSerializer(data={
            'type': 'agent', 'app_user': 'appuser', 'agent_setup': 'rotation',
            'service_name': 'sample-app', 'update_on_notification': False,
            'store_scope': 'selected', 'store_accounts': [str(self.primary.id)],
            'service_accounts': [
                {'account_id': str(self.primary.id), 'alias': 'database', 'username_field': 'DB_USER', 'secret_field': 'DB_PASSWORD'},
                {'account_id': str(cache.id), 'alias': 'cache', 'username_field': 'CACHE_USER', 'secret_field': 'CACHE_PASSWORD'},
            ],
            'config_file': '/etc/sample-app/config.yml', 'service_action_type': 'none',
            'application_check': '/usr/local/libexec/check-sample-app',
        }, context={'application': self.application})
        serializer.is_valid(raise_exception=True)
        config = json.loads(materials(self.application, serializer.validated_data, 'https://example.com')['config'])
        self.assertEqual(config['pull_interval'], 300)
        self.assertNotIn('reconcile_interval', config)
        self.assertEqual(config['store']['accounts'], [str(self.primary.id)])
        service = config['services'][0]
        self.assertTrue(service['allow_account_switch'])
        self.assertFalse(service['update_on_notification'])
        self.assertNotIn('allow_account_switch', service['accounts'][0])
        self.assertEqual(service['config_update']['fields_map']['CACHE_PASSWORD'], 'cache.secret')
        self.assertEqual(service['config_update']['fields_map']['DB_USER'], 'database.username')

    def test_wizard_rejects_duplicate_aliases_and_destination_fields(self):
        common = {'type': 'agent', 'app_user': 'appuser', 'agent_setup': 'config_update',
                  'config_file': '/etc/sample-app/config.yml', 'service_action_type': 'none'}
        for alias, field in [('database', 'CACHE_USER'), ('cache', 'DB_USER'), ('', 'CACHE_USER')]:
            serializer = CredentialAccessWizardSerializer(data={**common, 'service_accounts': [
                {'account_id': str(self.primary.id), 'alias': 'database', 'username_field': 'DB_USER', 'secret_field': 'DB_PASSWORD'},
                {'account_id': str(self.backup.id), 'alias': alias, 'username_field': field, 'secret_field': 'CACHE_PASSWORD'},
            ]}, context={'application': self.application})
            self.assertFalse(serializer.is_valid())
