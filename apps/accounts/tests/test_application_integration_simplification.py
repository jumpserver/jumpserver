import json
from uuid import uuid4

from accounts.api.account.credential import ApplicationCredentialViewSet
from accounts.credential_client.access import materials
from accounts.credential_client.manager import CredentialClientManager
from accounts.models import ApplicationCredential, IntegrationApplication
from accounts.serializers.account.credential import (
    ApplicationCredentialSerializer, CredentialAccessWizardSerializer,
)
from accounts.tests.base import CredentialTestCase


class ApplicationIntegrationSimplificationTests(CredentialTestCase):
    def wizard(self, **overrides):
        serializer = CredentialAccessWizardSerializer(data={
            'type': 'agent', 'app_user': 'orders', 'agent_setup': 'config_update',
            'account_id': str(self.primary.id), 'config_file': '/etc/orders/config.yml',
            'systemd_unit': 'orders.service', **overrides,
        }, context={'application': self.application})
        serializer.is_valid(raise_exception=True)
        return json.loads(materials(self.application, serializer.validated_data, 'https://example.com')['config'])

    def test_application_notifications_follow_authorization_without_a_policy(self):
        self.application.credential_notifications_enabled = True
        self.application.save(update_fields=['credential_notifications_enabled'])
        self.assertEqual(set(CredentialClientManager.credential_keys(self.application)), {
            self.credential.key, f'account:{self.primary.id}', f'account:{self.backup.id}',
        })
        self.application.accounts = {'type': 'ids', 'ids': [str(self.backup.id)]}
        self.application.save(update_fields=['accounts'])
        self.assertEqual(CredentialClientManager.credential_keys(self.application), [f'account:{self.backup.id}'])

    def test_config_wizard_generates_complete_update_and_service_rule(self):
        config = self.wizard()
        rule = config['services'][0]
        self.assertEqual(rule['accounts'], [{'id': str(self.primary.id)}])
        self.assertEqual(rule['update_config'], {
            'file': '/etc/orders/config.yml', 'format': 'auto',
            'fields_map': {'DB_USER': 'username', 'DB_PASSWORD': 'secret'},
        })
        self.assertEqual(rule['reload_service'], {'unit': 'orders.service', 'operation': 'restart'})
        self.assertNotIn('delivery', config)

    def test_wizard_exports_v1_storage_and_multiple_service_accounts(self):
        config = self.wizard(
            store_scope='selected', store_accounts=[str(self.backup.id)],
            service_name='orders', update_on_notification=False, allow_account_switch=True,
            service_accounts=[
                {'account_id': str(self.primary.id), 'alias': 'database',
                 'username_field': 'DB_USER', 'secret_field': 'DB_PASSWORD'},
                {'account_id': str(self.backup.id), 'alias': 'cache',
                 'username_field': 'CACHE_USER', 'secret_field': 'CACHE_PASSWORD'},
            ],
        )
        self.assertEqual(config['config_version'], 1)
        self.assertEqual(config['store']['accounts'], [str(self.backup.id)])
        service = config['services'][0]
        self.assertTrue(service['allow_account_switch'])
        self.assertFalse(service['update_on_notification'])
        self.assertEqual(service['update_config']['fields_map'], {
            'DB_USER': 'database.username', 'DB_PASSWORD': 'database.secret',
            'CACHE_USER': 'cache.username', 'CACHE_PASSWORD': 'cache.secret',
        })
        self.assertNotIn('rules', config)
        self.assertNotIn('store', self.wizard(store_scope='none'))

    def test_wizard_rejects_duplicate_mappings_and_unauthorized_storage(self):
        for overrides in (
            {'store_scope': 'selected', 'store_accounts': [str(uuid4())]},
            {'store_scope': 'selected', 'store_accounts': []},
            {'service_accounts': [{'account_id': str(self.primary.id), 'alias': 'same'},
                                  {'account_id': str(self.backup.id), 'alias': 'same'}]},
            {'service_accounts': [{'account_id': str(self.primary.id), 'alias': 'database'},
                                  {'account_id': str(self.backup.id), 'alias': 'cache'}]},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(Exception):
                self.wizard(**overrides)

    def test_generated_business_rules_do_not_offer_incompatible_foreground_installation(self):
        serializer = CredentialAccessWizardSerializer(data={
            'type': 'agent', 'app_user': 'orders', 'agent_setup': 'config_update',
            'account_id': str(self.primary.id), 'config_file': '/etc/orders/config.yml',
            'systemd_unit': 'orders.service',
        }, context={'application': self.application})
        serializer.is_valid(raise_exception=True)
        result = materials(self.application, serializer.validated_data, 'https://example.com')
        self.assertEqual(result['foreground_unix_command'], '')
        self.assertEqual(result['foreground_windows_command'], '')

    def test_rotation_wizard_requires_business_check_and_enables_switch(self):
        config = self.wizard(agent_setup='rotation', application_check='/usr/local/libexec/check-orders')
        rule = config['services'][0]
        self.assertTrue(rule['allow_account_switch'])
        self.assertEqual(rule['app_check'], {
            'path': '/usr/local/libexec/check-orders', 'confirm_on_success': True,
        })
        self.assertNotIn('app_check', self.wizard()['services'][0])

    def test_script_action_does_not_add_global_systemd_restart(self):
        config = self.wizard(service_action_type='script', service_script='/usr/local/libexec/recreate-orders')
        self.assertEqual(config['services'][0]['reload_service'], {'path': '/usr/local/libexec/recreate-orders'})
        self.assertNotIn('delivery', config)

    def test_invalid_wizard_materials_are_rejected(self):
        for overrides in (
            {'account_id': str(uuid4())}, {'config_file': 'config.yml'},
            {'agent_setup': 'rotation'}, {'secret_field': 'DB_USER'},
            {'service_action_type': 'script', 'service_script': 'relative/script'},
        ):
            with self.subTest(overrides=overrides):
                serializer = CredentialAccessWizardSerializer(data={
                    'type': 'agent', 'app_user': 'orders', 'agent_setup': 'config_update',
                    'account_id': str(self.primary.id), 'config_file': '/etc/orders/config.yml',
                    'systemd_unit': 'orders.service', **overrides,
                }, context={'application': self.application})
                self.assertFalse(serializer.is_valid())

    def test_policy_list_only_exposes_rotations(self):
        view = ApplicationCredentialViewSet.as_view({'get': 'list'})
        response = view(self.request('get', '/api/v1/accounts/application-credentials/', data={'limit': 10}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([str(row['id']) for row in response.data['results']], [str(self.credential.id)])
        response = view(self.request('get', '/api/v1/accounts/application-credentials/', data={'mode': 'subscription', 'limit': 10}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'], [])
