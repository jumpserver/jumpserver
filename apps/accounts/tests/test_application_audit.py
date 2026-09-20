import ast
import time
from contextlib import nullcontext
from unittest.mock import Mock, patch

from django.core.cache.backends.locmem import LocMemCache
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import force_authenticate
from redis.exceptions import ConnectionError as RedisConnectionError

from accounts.tests.base import CredentialTestCase
from accounts.models import ApplicationAudit, ClientAccessConfiguration, CredentialClientInstance
from accounts.credential_client.manager import CredentialClientManager
from accounts.credential_client.audit import record
from accounts.middleware import ApplicationAuditMiddleware
from accounts.api.account.application_audit import ApplicationAuditViewSet
from accounts.api.account.credential import CredentialClientViewSet
from orgs.utils import tmp_to_org
from orgs.models import Organization


class ApplicationAuditTests(CredentialTestCase):
    @staticmethod
    def client_response(request, action):
        view = CredentialClientViewSet.as_view({request.method.lower(): action})

        def get_response(raw_request):
            with transaction.atomic():
                return view(raw_request)

        return ApplicationAuditMiddleware(get_response)(request)

    def manager(self, instance='one'):
        configuration, _ = ClientAccessConfiguration.objects.get_or_create(
            application=self.application, name='Events SDK',
            defaults={'type': 'sdk'},
        )
        configuration.credentials.add(self.credential)
        manager = CredentialClientManager(self.application, configuration.id, instance)
        return manager, None

    def test_authorization_removal_disables_fetch_and_preserves_sibling(self):
        manager, _ = self.manager()
        manager.fetch(self.credential.key, '127.0.0.1')
        sibling_configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Sibling SDK', type='sdk',
        )
        sibling_configuration.credentials.add(self.credential)
        sibling = CredentialClientManager(
            self.application, sibling_configuration.id, 'sibling',
        )
        sibling.fetch(self.credential.key, '127.0.0.1')
        manager, _ = self.manager()
        configuration = manager.configuration
        configuration.credentials.remove(self.credential)
        self.assertFalse(
            manager.client.credential_statuses.filter(
                binding__credential=self.credential,
            ).exists()
        )
        self.assertTrue(
            sibling.client.credential_statuses.filter(
                binding__credential=self.credential,
            ).exists()
        )
        with self.assertRaises(PermissionDenied):
            manager.fetch(self.credential.key, '127.0.0.1')
        manager.client.is_active = False
        manager.client.save(update_fields=['is_active'])
        with self.assertRaises(PermissionDenied):
            CredentialClientManager(self.application, configuration.id, 'one')
        audit = ApplicationAudit.objects.filter(event='client_disabled').get()
        self.assertEqual(audit.instance_id, 'one')
        self.assertEqual(audit.configuration_id, configuration.id)

    def test_audit_org_scope_pagination_and_retained_history(self):
        record('credential_fetched', application=self.application)
        other_org = Organization.objects.create(name='Audit isolated org')
        with tmp_to_org(other_org):
            ApplicationAudit.objects.create(event='foreign')
        view = ApplicationAuditViewSet.as_view({'get': 'list'})
        request = self.request('get', '/api/v1/accounts/application-audits/', {'limit': 1, 'event': 'credential_fetched'})
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['service'], self.application.name)

    def test_failure_audit_survives_request_rollback(self):
        view = CredentialClientViewSet.as_view({'get': 'credential'})
        request = self.request('get', '/api/v1/accounts/credential-client/credential/',
                               {'key': 'missing', 'instance_id': 'rolled-back'}, self.application)
        def get_response(raw_request):
            with transaction.atomic():
                return view(raw_request)
        response = ApplicationAuditMiddleware(get_response)(request)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CredentialClientInstance.objects.filter(instance_id='rolled-back').exists())
        audit = ApplicationAudit.objects.get(event='credential_fetched', result='failed')
        self.assertEqual(audit.instance_id, 'rolled-back')

    def test_client_validation_failure_is_audited_before_manager_creation(self):
        request = self.factory.get('/api/v1/accounts/credential-client/credential/', {
            'key': self.credential.key, 'configuration_id': 'invalid-uuid', 'instance_id': 'invalid-request',
        }, HTTP_X_JMS_CLIENT_VERSION='1.0.0', HTTP_X_JMS_PROTOCOL_VERSION='1',
            HTTP_X_JMS_CONFIG_SCHEMA_VERSION='0')
        force_authenticate(request, user=self.application)
        response = self.client_response(request, 'credential')
        self.assertEqual(response.status_code, 400)
        audit = ApplicationAudit.objects.get(event='credential_fetched', result='failed')
        self.assertEqual(audit.service_id, self.application.id)
        self.assertEqual(audit.summary, 'invalid')
        self.assertFalse(CredentialClientInstance.objects.filter(instance_id='invalid-request').exists())

    def test_client_resolution_failure_keeps_validated_identity(self):
        manager, _ = self.manager()
        configuration = manager.configuration
        configuration.is_active = False
        configuration.save(update_fields=['is_active'])
        request = self.factory.get('/api/v1/accounts/credential-client/credential/', {
            'key': self.credential.key, 'configuration_id': str(configuration.id), 'instance_id': 'one',
        }, HTTP_X_JMS_CLIENT_VERSION='1.0.0', HTTP_X_JMS_PROTOCOL_VERSION='1',
            HTTP_X_JMS_CONFIG_SCHEMA_VERSION='0')
        force_authenticate(request, user=self.application)
        response = self.client_response(request, 'credential')
        self.assertEqual(response.status_code, 403)
        audit = ApplicationAudit.objects.get(event='credential_fetched', result='failed')
        self.assertEqual(audit.configuration_id, configuration.id)
        self.assertEqual(audit.instance_id, 'one')
        self.assertEqual(audit.credential_key, self.credential.key)

    def test_confirmation_failure_keeps_resolved_client(self):
        manager, _ = self.manager()
        request = self.factory.post('/api/v1/accounts/credential-client/confirm/', {
            'key': self.credential.key, 'configuration_id': str(manager.configuration.id),
            'instance_id': 'one', 'revision': self.credential.revision, 'account_id': str(self.primary.id),
        }, format='json', HTTP_X_JMS_CLIENT_VERSION='1.0.0',
            HTTP_X_JMS_PROTOCOL_VERSION='1', HTTP_X_JMS_CONFIG_SCHEMA_VERSION='0')
        force_authenticate(request, user=self.application)
        response = self.client_response(request, 'confirm')
        self.assertEqual(response.status_code, 400)
        audit = ApplicationAudit.objects.get(event='credential_confirmed', result='failed')
        self.assertEqual(audit.configuration_id, manager.configuration.id)
        self.assertEqual(audit.instance_id, manager.client.instance_id)
        self.assertEqual(audit.credential_key, self.credential.key)

    def test_configuration_audit_only_records_changed_fields(self):
        manager, _ = self.manager()
        configuration = manager.configuration
        audits = ApplicationAudit.objects.filter(event='configuration_updated', configuration_id=configuration.id)
        configuration.save(update_fields=['name'])
        self.assertFalse(audits.exists())
        previous = configuration.name
        configuration.name = 'Renamed SDK'
        configuration.save(update_fields=['name'])
        self.assertEqual(audits.get().changes, [{'field': 'name', 'before': previous, 'after': 'Renamed SDK'}])

    def test_revision_publication_takes_precedence_over_rotation_step(self):
        self.credential.revision += 1
        self.credential.status = 'waiting_primary'
        self.credential.save(update_fields=['revision', 'status'])
        audit = ApplicationAudit.objects.filter(credential_id=self.credential.id).latest('date_created')
        self.assertEqual(audit.event, 'credential_published')
        self.assertEqual({change['field'] for change in audit.changes}, {'revision', 'status'})

    def test_application_account_revocation_notifies_bound_clients(self):
        manager, _ = self.manager()
        manager.fetch(self.credential.key, '127.0.0.1')
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save(update_fields=['accounts'])
        audit = ApplicationAudit.objects.get(event='authorization_revoked', service_id=self.application.id)
        self.assertEqual(audit.credential_id, self.credential.id)

    def test_admin_actor_is_distinct_from_target_client(self):
        manager, _ = self.manager()
        request = Mock(user=self.admin, META={'REMOTE_ADDR': '127.0.0.1'})
        with patch('accounts.credential_client.audit.get_current_request', return_value=request):
            audit = record('client_disabled', client=manager.client)
        self.assertEqual(audit.source, 'Administrator')
        self.assertEqual(audit.operator, self.admin.name)
        self.assertEqual(audit.instance_id, 'one')

    def test_generated_sdk_code_polls_credentials_without_event_subscription(self):
        from accounts.credential_client.manager import ClientAccessConfigurationManager
        manager, _ = self.manager()
        self.application.secret = "secret'\n__import__('os').system('should-not-run')"
        self.application.save(update_fields=['secret'])
        materials = ClientAccessConfigurationManager(manager.configuration).materials('http://localhost')
        code = materials['code']
        compile(code, 'generated-sdk.py', 'exec')
        compile(materials['config'], materials['filename'], 'exec')
        config_tree = ast.parse(materials['config'])
        self.assertTrue(all(
            isinstance(node, (ast.ImportFrom, ast.Assign))
            for node in config_tree.body
        ))
        self.assertNotIn('PollEvents', code)
        self.assertIn('GetCredential', code)
        self.assertIn('time.sleep(30)', code)
        self.assertNotIn(self.application.secret, code)
        constants = [
            node.value for node in ast.walk(config_tree)
            if isinstance(node, ast.Constant)
        ]
        self.assertIn(self.application.secret, constants)

    def test_fixed_secret_publication(self):
        self.manager()
        self.credential.type = 'fixed'
        self.credential.backup_account = None
        self.credential.save()
        self.primary.secret = 'new-test-secret'
        self.primary.save()
        event = ApplicationAudit.objects.filter(event='credential_published', credential_id=self.credential.id).first()
        self.assertIsNotNone(event)
        self.primary.refresh_from_db()
        self.credential.refresh_from_db()
        self.assertEqual(event.revision, self.credential.revision)


class CredentialFetchAuditTestsMixin:
    def setUp(self):
        super().setUp()
        self.credential.rotation_mode = 'single'
        self.credential.save(update_fields=['rotation_mode'])
        self.client = self.create_client('one')
        self.audit_cache = LocMemCache(str(self.application.id), {})
        self.audit_cache.lock = lambda *args, **kwargs: nullcontext()
        self.addCleanup(self.audit_cache.clear)
        cache_patch = patch('accounts.credential_client.audit.cache', self.audit_cache)
        cache_patch.start()
        self.addCleanup(cache_patch.stop)

    def create_client(self, instance_id):
        configuration, _ = ClientAccessConfiguration.objects.get_or_create(
            application=self.application, name=self.client_type, defaults={'type': self.client_type},
        )
        configuration.credentials.add(self.credential)
        return CredentialClientInstance.objects.create(
            application=self.application, configuration=configuration,
            instance_id=instance_id, type=self.client_type,
        )

    def fetch(self, expected_status, key=None, client=None):
        client = client or self.client
        client = CredentialClientInstance.objects.select_related('application', 'configuration').get(pk=client.pk)
        request = self.factory.get('/api/v1/accounts/credential-client/credential/', {
            'key': key or self.credential.key,
            'configuration_id': str(client.configuration_id), 'instance_id': client.instance_id,
        }, HTTP_X_JMS_CLIENT_VERSION='1.0.0', HTTP_X_JMS_PROTOCOL_VERSION='1',
            HTTP_X_JMS_CONFIG_SCHEMA_VERSION='1' if self.client_type == 'agent' else '0')
        user = self.application if self.client_type == 'sdk' else client
        force_authenticate(request, user=user)
        response = ApplicationAuditMiddleware(self.get_response)(request)
        self.assertEqual(response.status_code, expected_status, response.data)
        return response

    @staticmethod
    def get_response(request):
        view = CredentialClientViewSet.as_view({'get': 'credential'})
        with transaction.atomic():
            return view(request)

    def set_credential(self, **values):
        for name, value in values.items():
            setattr(self.credential, name, value)
        self.credential.save(update_fields=list(values))

    def fetch_audits(self, **filters):
        return ApplicationAudit.objects.filter(event='credential_fetched', **filters)

    def test_unchanged_failure_does_not_write_even_after_a_day(self):
        self.set_credential(status='changing_secret')
        self.fetch(400)
        started = time.time()
        with CaptureQueriesContext(connection) as queries:
            for seconds in (1, 43200, 86400, 129600):
                with patch('time.time', return_value=started + seconds):
                    self.fetch(400)
        writes = [
            q['sql'] for q in queries
            if q['sql'].lstrip().startswith(('INSERT', 'UPDATE')) and 'accounts_applicationaudit' in q['sql']
        ]
        self.assertEqual(writes, [])
        self.assertEqual(self.fetch_audits(result='failed').count(), 1)

    def test_changed_error_records_a_new_failure(self):
        self.set_credential(status='changing_secret')
        self.fetch(400)
        self.set_credential(is_active=False)
        self.fetch(400)
        self.assertEqual(set(self.fetch_audits().values_list('summary', flat=True)), {
            'credential_changing', 'credential_not_found',
        })

    def test_different_credentials_have_independent_failure_states(self):
        self.set_credential(status='changing_secret')
        self.fetch(400)
        self.fetch(400, key='missing-key')
        self.fetch(400)
        self.fetch(400, key='missing-key')
        self.assertEqual(self.fetch_audits().count(), 2)

    def test_different_instances_have_independent_failure_states(self):
        other = self.create_client('two')
        self.set_credential(status='changing_secret')
        self.fetch(400)
        self.fetch(400, client=other)
        self.fetch(400, client=other)
        self.assertEqual(set(self.fetch_audits().values_list('instance_id', flat=True)), {'one', 'two'})
        self.assertEqual(self.fetch_audits().count(), 2)

    def test_recovery_of_same_version_is_recorded_once(self):
        self.fetch(200)
        self.set_credential(status='changing_secret')
        self.fetch(400)
        self.set_credential(status='idle')
        self.fetch(200)
        self.fetch(200)
        self.assertEqual(self.fetch_audits(result='success').count(), 2)
        self.assertEqual(self.fetch_audits(summary='Credential access recovered.').count(), 1)

    def test_failure_after_recovery_is_a_new_failure(self):
        self.set_credential(status='changing_secret')
        self.fetch(400)
        self.set_credential(status='idle')
        self.fetch(200)
        self.set_credential(status='changing_secret')
        self.fetch(400)
        self.assertEqual(self.fetch_audits(result='failed').count(), 2)

    def test_first_success_does_not_duplicate_recovery(self):
        self.set_credential(status='changing_secret')
        self.fetch(400)
        self.set_credential(status='idle')
        self.fetch(200)
        self.assertEqual(self.fetch_audits(result='success').count(), 1)

    def test_new_version_success_does_not_duplicate_recovery(self):
        self.fetch(200)
        self.set_credential(status='changing_secret')
        self.fetch(400)
        self.set_credential(status='idle', revision=self.credential.revision + 1)
        self.fetch(200)
        self.assertEqual(self.fetch_audits(result='success').count(), 2)
        self.assertFalse(self.fetch_audits(summary='Credential access recovered.').exists())

    def test_disabled_configuration_failure_can_recover(self):
        self.fetch(200)
        configuration = self.client.configuration
        configuration.is_active = False
        configuration.save(update_fields=['is_active'])
        self.fetch(403)
        self.fetch(403)
        self.assertEqual(self.fetch_audits(result='failed').count(), 1)
        configuration.is_active = True
        configuration.save(update_fields=['is_active'])
        self.fetch(200)
        self.assertEqual(self.fetch_audits(summary='Credential access recovered.').count(), 1)

    def test_cache_outage_preserves_failures_and_success_responses(self):
        self.fetch(200)
        with patch.object(self.audit_cache, 'get', side_effect=RedisConnectionError):
            self.fetch(200)
            self.set_credential(status='changing_secret')
            self.fetch(400)
        self.assertEqual(self.fetch_audits(result='success').count(), 1)
        self.assertEqual(self.fetch_audits(result='failed').count(), 1)

    def test_failed_audit_insert_does_not_consume_transition(self):
        self.set_credential(status='changing_secret')
        with patch('accounts.credential_client.audit.record', side_effect=RuntimeError('insert failed')):
            with self.assertRaisesRegex(RuntimeError, 'insert failed'):
                self.fetch(400)
        self.fetch(400)
        self.assertEqual(self.fetch_audits(result='failed').count(), 1)


class SDKFetchAuditTests(CredentialFetchAuditTestsMixin, CredentialTestCase):
    client_type = 'sdk'


class AgentFetchAuditTests(CredentialFetchAuditTestsMixin, CredentialTestCase):
    client_type = 'agent'
