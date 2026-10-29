import importlib
import json
from datetime import timedelta

from django.apps import apps
from django.db import connection, transaction
from django.test import override_settings
from django.urls import resolve, reverse
from django.utils import timezone

from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.api.account.application_audit import ApplicationAuditViewSet
from accounts.api.account.credential import CredentialClientViewSet
from accounts.credential_client.audit import record
from accounts.credential_client.manager import CredentialClientManager
from accounts.middleware import ApplicationAuditMiddleware
from accounts.models import ApplicationAudit, CredentialClientInstance, IntegrationApplication
from accounts.tests.base import CredentialTestCase
from audits.api import ServiceAccessLogViewSet
from audits.models import IntegrationApplicationLog
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org


class CredentialCallLogTests(CredentialTestCase):
    def calls(self):
        return IntegrationApplicationLog.objects.filter(service_id=self.application.id)

    def test_original_and_extended_filters_are_exposed_and_filter_records(self):
        own = IntegrationApplicationLog.objects.create(
            org_id=str(self.org.id), service=self.application.name, service_id=self.application.id,
            asset='Primary database', account='service-user', remote_addr='127.0.0.1',
            instance_id='demo-agent', source='Agent', result='success', revision=3,
            credential_key=self.credential.key,
        )
        other = IntegrationApplication.objects.create(name='Other application', secret='other-secret')
        IntegrationApplicationLog.objects.create(
            org_id=str(self.org.id), service=other.name, service_id=other.id,
            asset='Other database', account='other-user', remote_addr='127.0.0.2',
            instance_id='other-sdk', source='SDK', result='failed', revision=4,
        )
        view = ServiceAccessLogViewSet.as_view({'get': 'list'})
        metadata = view(self.request('options', '/', {'display': 1}))
        self.assertEqual(metadata.status_code, 200, metadata.data)
        self.assertTrue({
            'id', 'service', 'service_id', 'asset', 'account', 'remote_addr',
            'instance_id', 'source', 'result', 'credential_key', 'revision',
        }.issubset(metadata.data['filters']))
        self.assertEqual(metadata.data['filters']['source']['type'], 'choice')
        self.assertEqual(metadata.data['filters']['result']['type'], 'choice')
        self.assertIn('icontains', metadata.data['filters']['asset']['operators'])
        for query in (
            {'id': str(own.id)}, {'service': self.application.name},
            {'service_id': str(self.application.id)}, {'asset': own.asset},
            {'asset__icontains': 'Primary'}, {'account': own.account},
            {'remote_addr': own.remote_addr}, {'instance_id': own.instance_id},
            {'source': own.source}, {'result': own.result},
            {'credential_key': own.credential_key}, {'revision': own.revision},
        ):
            with self.subTest(query=query):
                response = view(self.request('get', '/', {**query, 'limit': 10}))
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data['count'], 1)
                self.assertEqual(response.data['results'][0]['id'], str(own.id))

    def test_sdk_and_agent_policy_fetches_record_every_call_without_secrets(self):
        for kind in ('sdk', 'agent'):
            client = CredentialClientInstance.objects.create(
                application=self.application, instance_id=f'call-{kind}', type=kind,
            )
            manager = (CredentialClientManager(client) if kind == 'agent'
                       else CredentialClientManager(self.application, instance_id=client.instance_id))
            for _ in range(3):
                manager.fetch(self.credential.key, '127.0.0.1')
            calls = self.calls().filter(instance_id=client.instance_id)
            self.assertEqual(calls.count(), 3)
            for call in calls:
                self.assertEqual(call.account, 'account-a(account-a)')
                self.assertEqual(call.asset, 'credential-test-pg(127.0.0.1)')
                self.assertEqual(call.org_id, str(self.org.id))
                self.assertEqual(call.credential_id, self.credential.id)
                self.assertEqual(call.account_id, self.primary.id)
                self.assertEqual(call.source, 'Agent' if kind == 'agent' else 'SDK')
                self.assertEqual(call.result, 'success')
                self.assertNotIn(self.primary.secret, json.dumps(call.__dict__, default=str))
            audits = ApplicationAudit.objects.filter(event='credential_fetched', instance_id=client.instance_id)
            self.assertEqual(audits.count(), 1)
            self.assertTrue(calls.filter(id=audits.get().id).exists())

    def test_raw_account_fetches_record_every_call_but_metadata_does_not(self):
        manager = CredentialClientManager(self.application, instance_id='account-calls')
        for _ in range(2):
            manager.fetch('', '127.0.0.1', self.primary.id)
        self.assertEqual(self.calls().count(), 2)
        manager.authorized_accounts()
        manager.application_info()
        self.assertEqual(self.calls().count(), 2)

    def legacy_request(self, account_id):
        request = self.request('get', '/', {'account_id': str(account_id)}, self.application)
        view = IntegrationApplicationViewSet.as_view({'get': 'get_account_secret'})
        def get_response(raw_request):
            with transaction.atomic():
                return view(raw_request)
        return ApplicationAuditMiddleware(get_response)(request)

    def test_legacy_endpoint_preserves_original_snapshots_and_records_each_call(self):
        with override_settings(SECURITY_DISABLE_VIEW_SECRET=False):
            for _ in range(2):
                response = self.legacy_request(self.primary.id)
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data['secret'], self.primary.secret)
        self.assertEqual(self.calls().count(), 2)
        self.assertEqual(self.calls().first().account, 'account-a(account-a)')

    def test_failed_requests_record_each_attempt_after_rollback(self):
        request_view = CredentialClientViewSet.as_view({'get': 'credential'})
        def get_response(raw_request):
            with transaction.atomic():
                return request_view(raw_request)
        for _ in range(2):
            request = self.request('get', '/', {'key': 'missing', 'instance_id': 'missing-calls'}, self.application)
            response = ApplicationAuditMiddleware(get_response)(request)
            self.assertEqual(response.status_code, 400)
        calls = self.calls().filter(instance_id='missing-calls', result='failed')
        self.assertEqual(calls.count(), 2)
        self.assertEqual(set(calls.values_list('remote_addr', flat=True)), {'127.0.0.1'})
        self.assertFalse(CredentialClientInstance.objects.filter(instance_id='missing-calls').exists())

    def test_legacy_failures_are_call_records(self):
        import uuid
        for _ in range(2):
            self.assertEqual(self.legacy_request(uuid.uuid4()).status_code, 400)
        self.assertEqual(self.calls().filter(result='failed').count(), 2)

    def test_old_route_fields_filters_and_org_isolation(self):
        own = IntegrationApplicationLog.objects.create(
            service=self.application.name, service_id=self.application.id,
            account='old-account', asset='old-asset', remote_addr='127.0.0.1',
        )
        other_org = Organization.objects.create(name='Other call logs')
        with tmp_to_org(other_org):
            other = IntegrationApplication.objects.create(name='other-app', secret='other-secret')
        foreign = IntegrationApplicationLog.objects.create(
            org_id=str(other_org.id), service=other.name, service_id=other.id,
            account='foreign', asset='foreign', remote_addr='127.0.0.2',
        )
        view = ServiceAccessLogViewSet.as_view({'get': 'list'})
        url = reverse('api-audits:service-access-log-list')
        self.assertIs(resolve(url).func.cls, ServiceAccessLogViewSet)
        response = view(self.request('get', url, {'service_id': str(self.application.id), 'account': 'old-account', 'limit': 10}))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], str(own.id))
        self.assertTrue({'id', 'service', 'service_id', 'asset', 'account', 'remote_addr', 'datetime'}.issubset(response.data['results'][0]))
        detail = ServiceAccessLogViewSet.as_view({'get': 'retrieve'})
        with transaction.atomic():
            self.assertEqual(detail(self.request('get', url), pk=foreign.id).status_code, 404)
        with tmp_to_root_org():
            self.assertEqual(view(self.request('get', url, {'limit': 10})).data['count'], 2)

    def test_calls_keep_scope_after_application_is_deleted(self):
        manager = CredentialClientManager(self.application, instance_id='retain')
        manager.fetch(self.credential.key, '127.0.0.1')
        app_id = self.application.id
        self.application.delete()
        response = ServiceAccessLogViewSet.as_view({'get': 'list'})(self.request('get', '/', {'service_id': str(app_id), 'limit': 10}))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 1)

    def test_event_tab_excludes_fetch_without_changing_existing_query_contract(self):
        record('credential_fetched', application=self.application)
        event = record('configuration_updated', application=self.application)
        view = ApplicationAuditViewSet.as_view({'get': 'list'})
        response = view(self.request('get', '/', {'application': str(self.application.id), 'exclude_event': 'credential_fetched', 'limit': 10}))
        self.assertIn(str(event.id), [row['id'] for row in response.data['results']])
        self.assertTrue(all(row['event'] != 'credential_fetched' for row in response.data['results']))
        response = view(self.request('get', '/', {'event': 'credential_fetched', 'limit': 10}))
        self.assertEqual(response.data['count'], 1)

    def test_event_log_exposes_and_applies_all_trace_filters(self):
        from uuid import uuid4
        ApplicationAudit.objects.all().delete()
        rotation_id, operation_id = uuid4(), uuid4()
        event = record(
            'notification', application=self.application, credential=self.credential,
            account=self.primary, instance_id='event-instance', source='Agent',
            operator='event-operator', remote_addr='127.0.0.1', result='failed',
            revision=42, operation_id=operation_id, summary='unique event detail',
        )
        ApplicationAudit.objects.filter(id=event.id).update(rotation_id=rotation_id)
        other = IntegrationApplication.objects.create(name='Other event application', secret='other-secret')
        record('configuration_updated', application=other, instance_id='other-instance', source='SDK')
        view = ApplicationAuditViewSet.as_view({'get': 'list'})
        metadata = view(self.request('options', '/'))
        self.assertEqual(metadata.status_code, 200, metadata.data)
        self.assertTrue({
            'id', 'event', 'service', 'service_id', 'credential', 'credential_id',
            'account', 'account_id', 'instance_id', 'operator', 'remote_addr',
            'source', 'result', 'revision', 'rotation_id', 'operation_id', 'summary',
        }.issubset(metadata.data['filters']))
        for query in (
            {'id': str(event.id)}, {'event': 'notification'}, {'service': self.application.name},
            {'service_id': str(self.application.id)}, {'credential': self.credential.name},
            {'credential_id': str(self.credential.id)}, {'credential_key': self.credential.key},
            {'account': self.primary.name}, {'account_id': str(self.primary.id)},
            {'instance_id': 'event-instance'}, {'operator': 'event-operator'},
            {'remote_addr': '127.0.0.1'}, {'source': 'Agent'}, {'result': 'failed'},
            {'revision': 42}, {'rotation_id': str(rotation_id)}, {'operation_id': str(operation_id)},
            {'summary__icontains': 'unique event'},
        ):
            with self.subTest(query=query):
                response = view(self.request('get', '/', {**query, 'exclude_event': 'credential_fetched', 'limit': 10}))
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data['count'], 1)
                self.assertEqual(response.data['results'][0]['id'], str(event.id))

    def test_backfill_preserves_ids_dates_old_rows_and_is_idempotent(self):
        old = IntegrationApplicationLog.objects.create(
            service=self.application.name, service_id=self.application.id,
            account='old(account)', asset='old(asset)', remote_addr='127.0.0.1',
        )
        date = timezone.now() - timedelta(days=10)
        IntegrationApplicationLog.objects.filter(id=old.id).update(datetime=date)
        audit = record('credential_fetched', application=self.application, account=self.primary)
        ApplicationAudit.objects.filter(id=audit.id).update(date_created=date)
        migration = importlib.import_module('audits.migrations.0011_backfill_application_credential_calls')
        with connection.schema_editor() as editor:
            migration.backfill_calls(apps, editor)
            migration.backfill_calls(apps, editor)
        self.assertEqual(self.calls().count(), 2)
        old.refresh_from_db()
        self.assertEqual(old.datetime, date)
        self.assertEqual(old.account, 'old(account)')
        self.assertEqual(old.org_id, str(self.org.id))
        migrated = self.calls().get(id=audit.id)
        self.assertEqual(migrated.datetime, date)
        self.assertEqual(migrated.asset, 'credential-test-pg(127.0.0.1)')
        self.assertEqual(migrated.account, 'account-a(account-a)')
