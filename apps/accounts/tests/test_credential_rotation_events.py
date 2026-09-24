from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from asgiref.sync import async_to_sync
from django.test import SimpleTestCase
from django.utils import timezone

from accounts.api.account.credential import ApplicationCredentialViewSet
from accounts.const import AuditEvent, ApplicationEvent, ChangeSecretRecordStatusChoice
from accounts.credential_client.audit import record
from accounts.credential_client.events import _publish_stream, enqueue
from accounts.credential_rotation.events import timeline, receive
from accounts.credential_rotation.manager import CredentialRotationManager
from accounts.models import (
    AutomationExecution, ChangeSecretRecord, ClientAccessConfiguration,
    CredentialClientInstance, CredentialRotationEvent, IntegrationApplication,
)
from accounts.tests.base import CredentialTestCase
from accounts.ws import CredentialEventConsumer


class RotationEventTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Rotation SDK', type='sdk',
        )
        self.configuration.credentials.add(self.credential)
        self.client = CredentialClientInstance.objects.create(
            application=self.application, configuration=self.configuration,
            instance_id='sdk-one', type='sdk', event_receipts_supported=True,
            date_last_seen=timezone.now(),
        )
        self.old_client = CredentialClientInstance.objects.create(
            application=self.application, configuration=self.configuration,
            instance_id='sdk-old', type='sdk',
        )
        self.manager = CredentialRotationManager(self.credential.id)
        self.manager.start()
        self.credential.refresh_from_db()
        self.rotation = self.credential.rotation_records.first()

    def publish(self):
        layer = Mock(group_send=AsyncMock())
        with patch('accounts.credential_client.events.get_channel_layer', return_value=layer):
            for event in self.rotation.events.all():
                _publish_stream(event.source_event_id, event.event)
        return layer

    def test_order_and_gap_do_not_infer_receipt_from_a_later_event(self):
        self.publish()
        events = list(self.rotation.events.all())
        self.assertEqual([event.event for event in events], [
            'credential.updated', 'rotation.started', 'rotation.waiting_for_application',
        ])
        self.assertEqual([event.sequence for event in events], [1, 2, 3])
        self.assertTrue(receive(self.client.id, self.org.id, events[2].source_event_id))
        self.assertTrue(receive(self.client.id, self.org.id, events[0].source_event_id))
        result = timeline(self.credential)
        client = next(row for row in result['instances'] if row['id'] == str(self.client.id))
        self.assertEqual(client['latest_event_id'], str(events[2].source_event_id))
        self.assertEqual((client['received_count'], client['event_count'], client['missing_count']), (2, 3, 1))
        self.assertIsNone(client['receipts'][1]['received_at'])
        old = next(row for row in result['instances'] if row['id'] == str(self.old_client.id))
        self.assertFalse(old['supports_receipts'])
        self.assertIsNone(old['latest_event_id'])
        self.assertEqual(old['received_count'], 0)

    def test_duplicate_invalid_and_wrong_scope_receipts(self):
        self.publish()
        event = self.rotation.events.first()
        for event_id in ('invalid', None, str(uuid4())):
            self.assertFalse(receive(self.client.id, self.org.id, event_id))
        self.assertFalse(receive(self.client.id, str(uuid4()), event.source_event_id))
        other_configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Other configuration', type='sdk',
        )
        CredentialClientInstance.objects.filter(id=self.client.id).update(configuration=other_configuration)
        self.assertFalse(receive(self.client.id, self.org.id, event.source_event_id))
        CredentialClientInstance.objects.filter(id=self.client.id).update(configuration=self.configuration)
        other_application = IntegrationApplication.objects.create(name='Other application')
        CredentialClientInstance.objects.filter(id=self.client.id).update(application=other_application)
        self.assertFalse(receive(self.client.id, self.org.id, event.source_event_id))
        CredentialClientInstance.objects.filter(id=self.client.id).update(application=self.application)
        outsider = CredentialClientInstance.objects.create(
            application=self.application, configuration=self.configuration,
            instance_id='joined-after-publication', type='sdk',
        )
        self.assertFalse(receive(outsider.id, self.org.id, event.source_event_id))
        self.assertTrue(receive(self.client.id, self.org.id, event.source_event_id))
        event.refresh_from_db()
        receipts = event.recipients
        self.assertTrue(receive(self.client.id, self.org.id, event.source_event_id))
        event.refresh_from_db()
        self.assertEqual(receipts, event.recipients)
        CredentialClientInstance.objects.filter(id=self.client.id).update(is_active=False)
        self.assertFalse(receive(self.client.id, self.org.id, event.source_event_id))

    def test_receipt_does_not_confirm_credentials_or_unblock_rotation(self):
        self.publish()
        before = self.credential.get_blockers()
        for event in self.rotation.events.all():
            receive(self.client.id, self.org.id, event.source_event_id)
            receive(self.old_client.id, self.org.id, event.source_event_id)
        self.assertEqual(before, self.credential.get_blockers())
        self.assertTrue(before)

    def test_group_send_failure_and_tracking_failure_do_not_block_source(self):
        layer = Mock(group_send=AsyncMock(side_effect=RuntimeError('unavailable')))
        event = self.rotation.events.first()
        with patch('accounts.credential_client.events.get_channel_layer', return_value=layer):
            _publish_stream(event.source_event_id, event.event)
        event.refresh_from_db()
        self.assertTrue(all(row['publish_result'] == 'failed' for row in event.recipients))
        audit = record(AuditEvent.ROTATION_STEP, credential=self.credential)
        with patch('accounts.credential_client.events._track_rotation', side_effect=RuntimeError()):
            enqueue(audit, ApplicationEvent.ROTATION_WAITING, rotation=self.rotation)
        self.assertFalse(CredentialRotationEvent.objects.filter(source_event_id=audit.id).exists())
        self.assertTrue(self.credential.rotation_records.exists())

    def test_completion_and_deleted_instances_keep_snapshot(self):
        self.publish()
        event = self.rotation.events.last()
        receive(self.client.id, self.org.id, event.source_event_id)
        self.manager._finish(self.credential, self.rotation, 'success')
        client_id = str(self.client.id)
        self.client.delete()
        result = timeline(self.credential)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['events'][-1]['event'], 'rotation.completed')
        client = next(row for row in result['instances'] if row['id'] == client_id)
        self.assertEqual(client['instance_id'], 'sdk-one')
        self.assertEqual(client['received_count'], 1)
        self.assertFalse(client['online'])
        self.assertFalse(client['is_active'])

    def test_explicit_rotation_association_ignores_stale_audit_rotation(self):
        self.manager._finish(self.credential, self.rotation, 'success')
        count = self.rotation.events.count()
        audit = record(AuditEvent.AUTHORIZATION_GRANTED, credential=self.credential)
        self.assertEqual(audit.rotation_id, self.rotation.id)
        enqueue(audit, ApplicationEvent.CREDENTIAL_UPDATED)
        self.assertEqual(self.rotation.events.count(), count)
        self.manager.start()
        current = self.credential.rotation_records.first()
        self.assertNotEqual(current.id, self.rotation.id)
        self.assertEqual(current.events.count(), 3)
        self.assertEqual(self.rotation.events.count(), count)

    def test_only_targeted_events_count_for_late_joiners(self):
        late = CredentialClientInstance.objects.create(
            application=self.application, configuration=self.configuration,
            instance_id='late-client', type='sdk',
        )
        audit = record(AuditEvent.SECRET_CHANGE_STARTED, credential=self.credential)
        enqueue(audit, ApplicationEvent.CREDENTIAL_CHANGE_STARTED, rotation=self.rotation)
        client = next(row for row in timeline(self.credential)['instances'] if row['id'] == str(late.id))
        self.assertEqual(client['event_count'], 1)
        self.assertEqual(client['receipts'][0]['event_id'], str(audit.id))

    def test_instance_registered_between_tracking_and_send_is_not_a_recipient(self):
        late = CredentialClientInstance.objects.create(
            application=self.application, configuration=self.configuration,
            instance_id='connected-before-send', type='sdk',
        )
        layer = self.publish()
        for call in layer.group_send.await_args_list:
            message = call.args[1]
            self.assertIn(str(self.client.id), message['recipient_ids'])
            self.assertNotIn(str(late.id), message['recipient_ids'])
            self.assertNotIn('recipient_ids', message['payload'])
        self.assertFalse(receive(late.id, self.org.id, self.rotation.events.first().source_event_id))

    def test_participants_are_visible_even_when_publication_tracking_was_unavailable(self):
        self.rotation.events.all().delete()
        result = timeline(self.credential)
        self.assertEqual(len(result['instances']), 2)
        self.assertTrue(all(row['event_count'] == 0 for row in result['instances']))

    def test_api_returns_receipts_without_secret_material(self):
        view = ApplicationCredentialViewSet.as_view({'get': 'rotation_events'})
        response = view(self.request('get', '/rotation-events/'), pk=self.credential.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['rotation_id'], str(self.rotation.id))
        self.assertNotIn('primary-secret', str(response.data))
        self.assertNotIn('application-secret', str(response.data))


class SubscriptionEventTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.credential.mode = self.credential.Mode.subscription
        self.credential.save(update_fields=['mode'])
        self.configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Subscription SDK', type='sdk',
        )
        self.configuration.credentials.add(self.credential)
        self.client = CredentialClientInstance.objects.create(
            application=self.application, configuration=self.configuration,
            instance_id='sdk-one', type='sdk', event_receipts_supported=True,
        )

    def test_subscription_events_use_receipt_timeline(self):
        audit = record(AuditEvent.SECRET_CHANGE_STARTED, credential=self.credential)
        enqueue(audit, ApplicationEvent.CREDENTIAL_CHANGE_STARTED)

        tracked = CredentialRotationEvent.objects.get(source_event_id=audit.id)
        self.assertIsNone(tracked.rotation_id)
        self.assertTrue(receive(self.client.id, self.org.id, audit.id))
        result = timeline(self.credential)

        self.assertEqual(result['events'][-1]['event'], 'credential.change.started')
        self.assertEqual(result['instances'][0]['received_count'], 1)

    def test_configuration_event_is_included(self):
        audit = record(AuditEvent.CONFIGURATION_UPDATED, configuration=self.configuration)
        enqueue(audit, ApplicationEvent.CONFIGURATION_UPDATED)

        result = timeline(self.credential)

        self.assertEqual(result['events'][-1]['event'], 'configuration.updated')

    def test_managed_password_change_tracks_events_and_receipts_without_rotation(self):
        previous_ids = list(CredentialRotationEvent.objects.values_list('id', flat=True))
        execution = AutomationExecution.objects.create(snapshot={}, org_id=self.org.id)
        change = ChangeSecretRecord.objects.create(
            account=self.primary, asset=self.asset, execution=execution,
            old_secret=self.primary.secret, new_secret='managed-secret',
        )
        self.primary.secret = change.new_secret
        self.primary.save()
        change.status = ChangeSecretRecordStatusChoice.success
        change.save(update_fields=['status'])

        events = list(CredentialRotationEvent.objects.exclude(
            id__in=previous_ids,
        ).order_by('published_at', 'id'))
        expected = [
            'credential.change.started', 'credential.change.completed', 'credential.updated',
        ]
        self.assertEqual([event.event for event in events], expected)
        self.assertTrue(all(event.rotation_id is None for event in events))
        layer = Mock(group_send=AsyncMock())
        with patch('accounts.credential_client.events.get_channel_layer', return_value=layer):
            for event in events:
                self.assertEqual([row['id'] for row in event.recipients], [str(self.client.id)])
                self.assertIsNone(event.recipients[0]['received_at'])
                _publish_stream(event.source_event_id, event.event)
                self.assertTrue(receive(self.client.id, self.org.id, event.source_event_id))
        self.assertEqual(layer.group_send.await_count, 3)
        result = timeline(self.credential)
        self.assertEqual([event['event'] for event in result['events'][-3:]], expected)
        self.assertEqual(result['instances'][0]['received_count'], 3)


class RotationReceiptConsumerTests(SimpleTestCase):
    def test_only_frozen_rotation_recipients_receive_event_but_normal_events_still_broadcast(self):
        consumer = CredentialEventConsumer()
        consumer.client = Mock(id=uuid4())
        consumer.send_json = AsyncMock()
        payload = {'event': 'credential.updated', 'event_id': str(uuid4())}
        message = {'payload': payload, 'recipient_ids': [str(uuid4())]}
        async_to_sync(consumer.credential_event)(message)
        consumer.send_json.assert_not_called()
        message['recipient_ids'].append(str(consumer.client.id))
        async_to_sync(consumer.credential_event)(message)
        consumer.send_json.assert_awaited_once_with(payload)
        consumer.send_json.reset_mock()
        async_to_sync(consumer.credential_event)({'payload': payload})
        consumer.send_json.assert_awaited_once_with(payload)

    def test_consumer_receipt_storage_failure_keeps_socket_usable(self):
        consumer = CredentialEventConsumer()
        consumer.client, consumer.org_id = Mock(id=uuid4()), str(uuid4())
        with patch('accounts.credential_rotation.events.receive', side_effect=RuntimeError()):
            async_to_sync(consumer.receive_json)({'event': 'received', 'event_id': str(uuid4())})
