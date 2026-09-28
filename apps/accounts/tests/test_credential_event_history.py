from uuid import uuid4

from django.db import transaction

from accounts.api.account.credential import ApplicationCredentialViewSet
from accounts.const import ApplicationEvent, AuditEvent
from accounts.credential_client.audit import record
from accounts.credential_client.events import enqueue
from accounts.credential_rotation.events import receive, timeline
from accounts.credential_rotation.history import directory, client_history
from accounts.credential_rotation.manager import CredentialRotationManager
from accounts.models import ClientAccessConfiguration, CredentialClientInstance
from accounts.tests.base import CredentialTestCase


class CredentialEventHistoryTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='History SDK', type='sdk',
        )
        self.configuration.credentials.add(self.credential)
        self.client = CredentialClientInstance.objects.create(
            application=self.application, configuration=self.configuration,
            instance_id='history-client', type='sdk', event_receipts_supported=True,
        )
        manager = CredentialRotationManager(self.credential.id)
        manager.start()
        self.first_rotation = self.credential.rotation_records.first()
        manager._finish(self.credential, self.first_rotation, 'success')
        manager.start()
        self.second_rotation = self.credential.rotation_records.first()

    def test_history_spans_rotations_and_separates_publication_from_receipt(self):
        first_event = self.first_rotation.events.first()
        receive(self.client.id, self.org.id, self.second_rotation.events.first().source_event_id)
        receive(self.client.id, self.org.id, first_event.source_event_id)
        result = client_history(self.credential, self.client.id, 2, 0)
        self.assertEqual(result['count'], 7)
        self.assertEqual(len(result['results']), 2)
        self.assertEqual(result['latest_event']['rotation_id'], str(self.second_rotation.id))
        self.assertEqual(result['latest_received_event']['id'], str(first_event.source_event_id))
        older = client_history(self.credential, self.client.id, 10, 2)
        self.assertEqual(len(older['results']), 5)
        self.assertNotIn(result['results'][0]['id'], [event['id'] for event in older['results']])
        comparison = timeline(self.credential, self.first_rotation.id)
        self.assertEqual(comparison['rotation_id'], str(self.first_rotation.id))
        self.assertEqual(len(comparison['events']), 4)

    def test_deleted_client_remains_in_directory_and_history(self):
        client_id = self.client.id
        self.client.delete()
        rows = directory(self.credential, 'history-client', 'sdk', 'inactive')
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]['is_active'])
        result = client_history(self.credential, client_id, 30, 0)
        self.assertEqual(result['count'], 7)
        self.assertFalse(result['client']['is_active'])

    def test_subscription_history_and_removed_binding_keep_existing_receipts(self):
        CredentialRotationManager(self.credential.id)._finish(self.credential, self.second_rotation, 'success')
        self.credential.mode = self.credential.Mode.subscription
        self.credential.save(update_fields=['mode'])
        audit = record(AuditEvent.SECRET_CHANGE_STARTED, credential=self.credential)
        enqueue(audit, ApplicationEvent.CREDENTIAL_CHANGE_STARTED)
        receive(self.client.id, self.org.id, audit.id)
        before = client_history(self.credential, self.client.id, 30, 0)
        self.assertEqual(before['latest_event']['event'], 'credential.change.started')
        self.configuration.credentials.remove(self.credential)
        result = client_history(self.credential, self.client.id, 30, 0)
        self.assertEqual(result['count'], before['count'] + 1)
        self.assertEqual(result['results'][0]['event'], 'credential.revoked')
        self.assertEqual(result['results'][1:], before['results'])
        self.assertTrue(all(event['rotation_id'] is None for event in result['results']))
        self.assertEqual(result['client']['is_active'], directory(self.credential)[0]['is_active'])
        self.assertEqual(result['latest_received_event']['id'], str(audit.id))

    def test_new_client_has_empty_history_without_inheriting_earlier_events(self):
        late = CredentialClientInstance.objects.create(
            application=self.application, configuration=self.configuration,
            instance_id='late-agent', type='agent',
        )
        result = client_history(self.credential, late.id, 30, 0)
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['results'], [])
        self.assertIsNone(result['latest_event'])
        self.assertEqual(len(directory(self.credential, client_type='agent')), 1)

    def test_api_limits_filters_and_scope(self):
        view = ApplicationCredentialViewSet.as_view({'get': 'event_history'})
        for params in ({'limit': 101}, {'offset': -1}, {'client_id': 'bad'}, {'state': 'bad'}):
            with transaction.atomic():
                response = view(self.request('get', '/event-history/', params), pk=self.credential.id)
            self.assertEqual(response.status_code, 400)
        with transaction.atomic():
            response = view(self.request('get', '/event-history/', {'client_id': str(uuid4())}), pk=self.credential.id)
        self.assertEqual(response.status_code, 404)
        response = view(self.request('get', '/event-history/', {'client_search': 'History SDK', 'limit': 1}), pk=self.credential.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertNotIn('primary-secret', str(response.data))
        self.assertEqual(directory(self.credential, client_type='agent'), [])
        self.assertEqual(directory(self.credential, state='online'), [])
        self.assertEqual(len(directory(self.credential, state='offline')), 1)
        self.credential.org_id = str(uuid4())
        self.assertEqual(directory(self.credential), [])
