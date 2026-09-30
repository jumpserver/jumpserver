from contextlib import nullcontext
from unittest.mock import Mock, patch

from accounts.api.account.application_audit import ApplicationAuditViewSet
from accounts.api.account.credential import CredentialClientViewSet
from accounts.credential_client.audit import record
from accounts.credential_client.manager import CredentialClientManager
from accounts.middleware import ApplicationAuditMiddleware
from accounts.models import (
    ApplicationAudit,
    ApplicationCredential,
    CredentialApplicationBinding,
    CredentialClientInstance,
)
from accounts.tests.base import CredentialTestCase
from django.core.cache.backends.locmem import LocMemCache
from django.db import transaction
from orgs.models import Organization
from orgs.utils import tmp_to_org
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import force_authenticate


class ApplicationAuditTests(CredentialTestCase):
    @staticmethod
    def client_response(request, action):
        view = CredentialClientViewSet.as_view({request.method.lower(): action})

        def get_response(raw_request):
            with transaction.atomic():
                return view(raw_request)

        return ApplicationAuditMiddleware(get_response)(request)

    def manager(self, instance='one'):
        return CredentialClientManager(self.application, instance_id=instance), None

    def test_authorization_removal_disables_fetch_for_all_application_instances(self):
        manager, _ = self.manager()
        manager.fetch(self.credential.key, '127.0.0.1')
        sibling = CredentialClientManager(self.application, instance_id='sibling')
        sibling.fetch(self.credential.key, '127.0.0.1')
        manager, _ = self.manager()
        self.credential.applications.remove(self.application)
        self.assertFalse(
            manager.client.credential_statuses.filter(
                binding__credential=self.credential,
            ).exists()
        )
        self.assertFalse(
            sibling.client.credential_statuses.filter(
                binding__credential=self.credential,
            ).exists()
        )
        with self.assertRaises(PermissionDenied):
            manager.fetch(self.credential.key, '127.0.0.1')
        manager.client.is_active = False
        manager.client.save(update_fields=['is_active'])
        with self.assertRaises(PermissionDenied):
            CredentialClientManager(self.application, instance_id='one')
        audit = ApplicationAudit.objects.filter(event='client_disabled').get()
        self.assertEqual(audit.instance_id, 'one')

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

    def test_disabled_instance_failure_keeps_request_identity(self):
        manager, _ = self.manager()
        manager.client.is_active = False
        manager.client.save(update_fields=['is_active'])
        request = self.factory.get('/api/v1/accounts/credential-client/credential/', {
            'key': self.credential.key, 'instance_id': 'one',
        }, HTTP_X_JMS_CLIENT_VERSION='1.0.0', HTTP_X_JMS_PROTOCOL_VERSION='1',
            HTTP_X_JMS_CONFIG_SCHEMA_VERSION='0')
        force_authenticate(request, user=self.application)
        response = self.client_response(request, 'credential')
        self.assertEqual(response.status_code, 403)
        audit = ApplicationAudit.objects.get(event='credential_fetched', result='failed')
        self.assertEqual(audit.instance_id, 'one')
        self.assertEqual(audit.credential_key, self.credential.key)

    def test_confirmation_failure_keeps_resolved_client(self):
        manager, _ = self.manager()
        request = self.factory.post('/api/v1/accounts/credential-client/confirm/', {
            'key': self.credential.key, 'instance_id': 'one',
            'revision': self.credential.revision, 'account_id': str(self.primary.id),
        }, format='json', HTTP_X_JMS_CLIENT_VERSION='1.0.0',
            HTTP_X_JMS_PROTOCOL_VERSION='1', HTTP_X_JMS_CONFIG_SCHEMA_VERSION='0')
        force_authenticate(request, user=self.application)
        response = self.client_response(request, 'confirm')
        self.assertEqual(response.status_code, 400)
        audit = ApplicationAudit.objects.get(event='credential_confirmed', result='failed')
        self.assertEqual(audit.instance_id, manager.client.instance_id)
        self.assertEqual(audit.credential_key, self.credential.key)

    def test_revision_publication_takes_precedence_over_rotation_step(self):
        self.credential.revision += 1
        self.credential.status = 'waiting_revert'
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


    def test_subscription_secret_publication(self):
        self.manager()
        self.credential.mode = ApplicationCredential.Mode.subscription
        self.credential.account = None
        self.credential.alternate_account = None
        self.credential.active_account = None
        self.credential.save()
        self.credential.subscription_accounts.add(self.primary)
        self.primary.secret = 'new-test-secret'
        self.primary.save()
        event = ApplicationAudit.objects.filter(
            event='credential_published', credential_id=self.credential.id,
            account_id=self.primary.id,
        ).first()
        self.assertIsNotNone(event)
        self.primary.refresh_from_db()
        self.credential.refresh_from_db()
        self.assertEqual(event.revision, self.primary.version)
        self.assertEqual(event.account_id, self.primary.id)
        self.assertEqual(event.credential_key, self.credential.account_key(self.primary.id))


class CredentialFetchAuditTestsMixin:
    def setUp(self):
        super().setUp()
        self.client = self.create_client('one')
        self.audit_cache = LocMemCache(str(self.application.id), {})
        self.audit_cache.lock = lambda *args, **kwargs: nullcontext()
        self.addCleanup(self.audit_cache.clear)
        cache_patch = patch('accounts.credential_client.audit.cache', self.audit_cache)
        cache_patch.start()
        self.addCleanup(cache_patch.stop)

    def create_client(self, instance_id):
        return CredentialClientInstance.objects.create(
            application=self.application,
            instance_id=instance_id, type=self.client_type,
        )

    def fetch(self, expected_status, key=None, client=None):
        client = client or self.client
        client = CredentialClientInstance.objects.select_related('application').get(pk=client.pk)
        request = self.factory.get('/api/v1/accounts/credential-client/credential/', {
            'key': key or self.credential.key, 'instance_id': client.instance_id,
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

    def test_different_credentials_have_independent_failure_states(self):
        self.fetch(400, key='missing-one')
        self.fetch(400, key='missing-two')
        self.fetch(400, key='missing-one')
        self.assertEqual(self.fetch_audits().count(), 2)

    def test_different_instances_have_independent_failure_states(self):
        other = self.create_client('two')
        self.fetch(400, key='missing-key')
        self.fetch(400, key='missing-key', client=other)
        self.fetch(400, key='missing-key', client=other)
        self.assertEqual(set(self.fetch_audits().values_list('instance_id', flat=True)), {'one', 'two'})
        self.assertEqual(self.fetch_audits().count(), 2)

    def test_revoked_binding_failure_can_fetch_after_regrant(self):
        self.fetch(200)
        self.credential.applications.remove(self.application)
        self.fetch(403)
        self.fetch(403)
        self.assertEqual(self.fetch_audits(result='failed').count(), 1)
        CredentialApplicationBinding.objects.create(
            credential=self.credential, application=self.application, org_id=self.org.id,
        )
        self.fetch(200)
        self.assertEqual(self.fetch_audits(result='success').count(), 2)

    def test_cache_outage_preserves_failures_and_success_responses(self):
        self.fetch(200)
        with patch.object(self.audit_cache, 'get', side_effect=RedisConnectionError):
            self.fetch(200)
            self.fetch(400, key='missing-key')
        self.assertEqual(self.fetch_audits(result='success').count(), 1)
        self.assertEqual(self.fetch_audits(result='failed').count(), 1)

    def test_failed_audit_insert_does_not_consume_transition(self):
        with patch('accounts.credential_client.audit.record', side_effect=RuntimeError('insert failed')):
            with self.assertRaisesRegex(RuntimeError, 'insert failed'):
                self.fetch(400, key='missing-key')
        self.fetch(400, key='missing-key')
        self.assertEqual(self.fetch_audits(result='failed').count(), 1)


class SDKFetchAuditTests(CredentialFetchAuditTestsMixin, CredentialTestCase):
    client_type = 'sdk'


class AgentFetchAuditTests(CredentialFetchAuditTestsMixin, CredentialTestCase):
    client_type = 'agent'
