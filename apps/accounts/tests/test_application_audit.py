import ast
import json
import threading
import time
from contextlib import nullcontext
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock, patch

import requests
from django.core.cache.backends.locmem import LocMemCache
from django.db import connection, transaction
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import force_authenticate
from redis.exceptions import ConnectionError as RedisConnectionError

from accounts.tests.base import CredentialTestCase
from accounts.models import ApplicationAudit, ApplicationEventDelivery, ClientAccessConfiguration, CredentialClientInstance
from accounts.credential_client.manager import CredentialClientManager
from accounts.credential_client.events import ClientEventManager, enqueue
from accounts.credential_client.audit import record
from accounts.middleware import ApplicationAuditMiddleware
from accounts.api.account.application_audit import ApplicationAuditViewSet
from accounts.serializers.account.credential import EventReportSerializer
from accounts.api.account.credential import CredentialClientViewSet
from accounts.demos.python.jms_pam.events import EventWorker, DeliveryError
from accounts.demos.python.jms_pam.agent import Agent
from accounts.demos.python.jms_pam.main import CredentialAPIClient
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

    def manager(self, instance='one', enabled=True):
        configuration, _ = ClientAccessConfiguration.objects.get_or_create(
            application=self.application, name='Events SDK',
            defaults={'type': 'sdk', 'notification_enabled': enabled},
        )
        configuration.credentials.add(self.credential)
        manager = CredentialClientManager(self.application, configuration.id, instance)
        return manager, ClientEventManager(manager)

    def test_optional_subscription_delivery_and_confirmation_are_independent(self):
        manager, events = self.manager()
        self.assertFalse(events.poll()['enabled'])
        manager.fetch(self.credential.key, '127.0.0.1')
        events.subscribe(True)
        # Refresh manager, like a new HTTP request.
        manager, events = self.manager()
        message = events.poll()['events'][0]
        self.assertEqual(message['event'], 'credential.published')
        self.assertNotIn('secret', json.dumps(message, default=str))
        with self.assertRaises(ValidationError):
            events.report('00000000-0000-0000-0000-000000000000', 'success')
        events.report(message['attempt_id'], 'success')
        events.report(message['attempt_id'], 'success')
        self.assertEqual(ApplicationEventDelivery.objects.get(id=message['delivery_id']).attempts.count(), 1)
        state = manager.client.credential_statuses.get()
        self.assertEqual(state.applied_revision, 0)
        manager.confirm(self.credential.key, self.credential.revision, self.primary.id)
        manager.confirm(self.credential.key, self.credential.revision, self.primary.id)
        manager.heartbeat([{'key': self.credential.key, 'revision': self.credential.revision, 'account_id': self.primary.id}])
        self.assertEqual(ApplicationAudit.objects.filter(event='credential_confirmed').count(), 1)
        self.assertFalse(events.poll()['events'])
        self.assertNotIn('primary-secret', json.dumps(list(ApplicationAudit.objects.values()), default=str))

    def test_retry_identity_ownership_and_deadline(self):
        manager, events = self.manager()
        events.subscribe(True)
        manager, events = self.manager()
        first = events.poll()['events'][0]
        _, other = self.manager('other')
        with self.assertRaises(ValidationError):
            other.report(first['attempt_id'], 'success')
        self.assertEqual(events.poll()['events'], [])  # Claim is leased, not delivered twice concurrently.
        for number in range(1, 6):
            current = first if number == 1 else events.poll()['events'][0]
            self.assertEqual(current['event_id'], first['event_id'])
            events.report(current['attempt_id'], 'failed', reason='callback_failed')
            delivery = ApplicationEventDelivery.objects.get(id=first['delivery_id'])
            self.assertEqual(delivery.attempts.count(), number)
            ApplicationEventDelivery.objects.filter(id=delivery.id).update(available_at=timezone.now())
        self.assertEqual(events.poll()['events'], [])
        delivery.refresh_from_db()
        self.assertEqual(delivery.audit.result, 'failed')

    def test_authorization_removal_delivers_only_revocation_and_disable_rejects(self):
        manager, events = self.manager()
        manager.fetch(self.credential.key, '127.0.0.1')
        sibling_configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Sibling SDK', type='sdk',
        )
        sibling_configuration.credentials.add(self.credential)
        sibling = CredentialClientManager(
            self.application, sibling_configuration.id, 'sibling',
        )
        sibling.fetch(self.credential.key, '127.0.0.1')
        events.subscribe(True)
        published = ApplicationEventDelivery.objects.get(
            client=manager.client, code='credential.published', status='pending',
        )
        manager, events = self.manager()
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
        published.refresh_from_db()
        published.audit.refresh_from_db()
        self.assertEqual(published.status, 'failed')
        self.assertEqual(published.audit.result, 'failed')
        self.assertEqual(
            list(ApplicationEventDelivery.objects.filter(
                client=manager.client, status='pending',
            ).values_list('code', flat=True)),
            ['access.revoked'],
        )
        with self.assertRaises(PermissionDenied):
            manager.fetch(self.credential.key, '127.0.0.1')
        messages = events.poll()['events']
        self.assertEqual([message['event'] for message in messages], ['access.revoked'])
        manager.client.is_active = False
        manager.client.save(update_fields=['is_active'])
        with self.assertRaises(PermissionDenied):
            CredentialClientManager(self.application, configuration.id, 'one')
        audit = ApplicationAudit.objects.filter(event='client_disabled').get()
        self.assertEqual(audit.instance_id, 'one')
        self.assertEqual(audit.configuration_id, configuration.id)

    def test_revocation_closes_stale_delivery_while_listener_is_paused(self):
        manager, events = self.manager()
        events.subscribe(True)
        published = ApplicationEventDelivery.objects.get(
            client=manager.client, code='credential.published', status='pending',
        )
        CredentialClientInstance.objects.filter(id=manager.client.id).update(events_enabled=False)

        manager.configuration.credentials.remove(self.credential)

        published.refresh_from_db()
        self.assertEqual(published.status, 'failed')
        self.assertFalse(
            ApplicationEventDelivery.objects.filter(
                client=manager.client, code='access.revoked',
            ).exists()
        )

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
        })
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
        })
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
        }, format='json')
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
        manager, events = self.manager()
        manager.fetch(self.credential.key, '127.0.0.1')
        events.subscribe(True)
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save(update_fields=['accounts'])
        audit = ApplicationAudit.objects.get(event='authorization_revoked', service_id=self.application.id)
        self.assertEqual(audit.credential_id, self.credential.id)
        self.assertEqual(list(audit.deliveries.values_list('code', flat=True)), ['access.revoked'])

    def test_subscribers_share_event_id_and_expiration_closes_audit(self):
        for name in ('one', 'two'):
            _, events = self.manager(name)
            events.subscribe(True)
        event = record('credential_published', credential=self.credential)
        enqueue(event, 'credential.published')
        self.assertEqual(event.deliveries.count(), 2)
        from accounts.tasks.application_events import expire_application_event_deliveries
        event.deliveries.update(expires_at=timezone.now() - timedelta(seconds=1))
        expire_application_event_deliveries()
        self.assertEqual(set(event.deliveries.values_list('audit__result', flat=True)), {'failed'})

    def test_admin_actor_is_distinct_from_target_client(self):
        manager, _ = self.manager()
        request = Mock(user=self.admin, META={'REMOTE_ADDR': '127.0.0.1'})
        with patch('accounts.credential_client.audit.get_current_request', return_value=request):
            audit = record('client_disabled', client=manager.client)
        self.assertEqual(audit.source, 'Administrator')
        self.assertEqual(audit.operator, self.admin.name)
        self.assertEqual(audit.instance_id, 'one')

    def test_no_notification_auth_and_safe_result_payload(self):
        data = EventReportSerializer(data={'attempt_id': self.application.id, 'result': 'failed', 'reason': 'secret text'})
        self.assertFalse(data.is_valid())
        _, events = self.manager(enabled=False)
        self.assertFalse(events.subscribe(True)['enabled'])

    def test_sdk_and_agent_use_same_event_actions_and_real_audit_detail(self):
        for client_type in ('sdk', 'agent'):
            configuration = ClientAccessConfiguration.objects.create(
                application=self.application, name=f'HTTP {client_type}', type=client_type,
                notification_enabled=True,
                notification_url='http://127.0.0.1:9000/events' if client_type == 'agent' else '',
            )
            configuration.credentials.add(self.credential)
            user = self.application
            if client_type == 'agent':
                user = CredentialClientInstance.objects.create(
                    configuration=configuration, application=self.application, instance_id='agent-http', type='agent',
                )
            def event_request(action, **data):
                data.update(configuration_id=str(configuration.id), instance_id=f'{client_type}-http')
                request = self.factory.post('/api/v1/accounts/credential-client/events/', data, format='json')
                force_authenticate(request, user=user)
                method = {'': 'events', 'subscribe': 'subscribe_events', 'report': 'report_event'}[action]
                response = CredentialClientViewSet.as_view({'post': method})(request)
                self.assertEqual(response.status_code, 200, response.data)
                return response.data
            event_request('subscribe', enabled=True)
            remote = Mock(source='jms-pam-agent' if client_type == 'agent' else 'jms-pam')
            remote.event_request.side_effect = event_request
            handler = Mock(return_value=204)
            EventWorker(remote, handler).step()
            handler.assert_called_once()
            audit = ApplicationAudit.objects.filter(event='notification', configuration_id=configuration.id).get()
            self.assertEqual(audit.result, 'success')
            request = self.request('get', f'/api/v1/accounts/application-audits/{audit.id}/')
            response = ApplicationAuditViewSet.as_view({'get': 'retrieve'})(request, pk=audit.id)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data['notification']['attempts']), 1)
            self.assertNotIn('secret', response.render().content.decode())

    def test_generated_sdk_code_with_optional_notifications(self):
        from accounts.credential_client.manager import ClientAccessConfigurationManager
        manager, _ = self.manager()
        for enabled in (True, False):
            with self.subTest(notification_enabled=enabled):
                manager.configuration.notification_enabled = enabled
                materials = ClientAccessConfigurationManager(manager.configuration).materials('http://localhost')
                code = materials['code']
                compile(code, 'generated-sdk.py', 'exec')
                self.assertEqual(materials['config']['notification_enabled'], enabled)
                self.assertEqual('def on_event(event):' in code, enabled)
                self.assertEqual('client.start_events(handler=on_event)' in code, enabled)
                loop = next(node for node in ast.walk(ast.parse(code)) if isinstance(node, ast.For))
                self.assertEqual(ast.literal_eval(loop.iter), materials['config']['credential_keys'])
                self.assertIn('except requests.RequestException as error:', code)
                self.assertIn('time.sleep(30)', code)
                self.assertNotIn(self.application.secret, code)

    def test_fixed_secret_publication(self):
        manager, events = self.manager()
        self.credential.type = 'fixed'
        self.credential.backup_account = None
        self.credential.save()
        events.subscribe(True)
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
        })
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


class EventWorkerTests(SimpleTestCase):
    def test_agent_http_delivery_against_local_application(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append((dict(self.headers), json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(500 if len(received) == 1 else 204)
                self.end_headers()

            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        agent = Agent.__new__(Agent)
        agent.config = {'notification_url': f'http://127.0.0.1:{server.server_port}/events'}
        agent.notification_session = requests.Session()
        agent.notification_session.trust_env = False
        event = {'event': 'credential.unavailable', 'event_id': 'test-event', 'key': 'test-key', 'revision': 2}
        try:
            with self.assertRaises(DeliveryError) as error:
                agent.notify(event, None)
            self.assertEqual(error.exception.status_code, 500)
            self.assertEqual(agent.notify(event, None), 204)
            self.assertEqual(received[0][1], received[1][1])
            self.assertNotIn('Authorization', received[0][0])
            self.assertEqual(received[0][1], event)
        finally:
            server.shutdown()
            server.server_close()
            agent.notification_session.close()
            thread.join()

    def test_report_network_retry_does_not_repeat_callback(self):
        remote = Mock(source='jms-pam')
        event = {'attempt_id': 'attempt', 'delivery_id': 'delivery', 'event_id': 'event',
                 'event': 'credential.published', 'key': 'db', 'revision': 2}
        remote.event_request.side_effect = [
            {'enabled': True, 'events': [event]}, requests.ConnectionError(),
            {'result': 'success'}, {'enabled': True, 'events': []},
        ]
        handler = Mock()
        worker = EventWorker(remote, handler)
        with self.assertRaises(requests.ConnectionError):
            worker.step()
        worker.step()
        self.assertEqual(handler.call_count, 1)
        self.assertNotIn('attempt_id', handler.call_args.args[0])
        self.assertIsNone(worker.pending_report)
        self.assertEqual(remote.event_request.call_args_list[1], remote.event_request.call_args_list[2])

    def test_callback_failure_does_not_leak_exception_or_confirm(self):
        remote = Mock(source='jms-pam')
        worker = EventWorker(remote, Mock(side_effect=ValueError('PASSWORD')))
        worker.deliver({'attempt_id': 'attempt', 'event_id': 'event'})
        self.assertEqual(worker.pending_report, {'attempt_id': 'attempt', 'result': 'failed', 'reason': 'callback_failed'})
        remote.confirm.assert_not_called()

    def test_agent_writes_before_notification_and_exact_confirmation(self):
        agent = Agent.__new__(Agent)
        agent.config = {'notification_url': 'http://127.0.0.1:9000/events'}
        agent.lock = threading.Lock()
        agent.credentials = {'db': {'revision': 2, 'account_id': 'account'}}
        agent.notification_session = Mock()
        agent.notification_session.post.return_value.status_code = 204
        order = []
        agent.poll = Mock(side_effect=lambda **kwargs: order.append('write'))
        agent.notification_session.post.side_effect = lambda *a, **kw: (order.append('notify') or Mock(status_code=204))
        event = {'event': 'credential.published', 'key': 'db', 'revision': 2}
        self.assertEqual(agent.notify(event, Mock()), 204)
        self.assertEqual(order, ['write', 'notify'])
        self.assertFalse(agent.notification_session.post.call_args.kwargs['allow_redirects'])
        event['revision'] = 1
        with self.assertRaises(DeliveryError):
            agent.notify(event, Mock())
        self.assertEqual(agent.notification_session.post.call_count, 1)
        with self.assertRaises(ValueError):
            agent.confirm('db', 1)

    def test_listener_has_own_http_session(self):
        remote = CredentialAPIClient('http://localhost', 'id', 'secret', instance_id='one', configuration_id='config')
        other = remote.fork()
        self.assertIsNot(remote.session, other.session)
        self.assertEqual(other.configuration_id, 'config')
        self.assertEqual(other.instance_id, 'one')
        remote.session.close()
        other.session.close()
