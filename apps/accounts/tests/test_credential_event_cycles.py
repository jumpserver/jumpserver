from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from accounts.api.account.credential import ApplicationCredentialViewSet
from accounts.const import ApplicationEvent, AuditEvent
from accounts.credential_client.audit import record
from accounts.credential_client.events import enqueue, _publish_stream
from accounts.credential_client.manager import CredentialClientManager
from accounts.credential_rotation.cycles import cycle_directory, cycle_detail
from accounts.credential_rotation.events import receive
from accounts.credential_rotation.manager import CredentialRotationManager
from accounts.models import (
    ApplicationCredential, AutomationExecution, ChangeSecretRecord,
    CredentialApplicationBinding,
    CredentialClientInstance, CredentialRotationEvent,
)
from accounts.tests.base import CredentialTestCase


class CredentialEventCycleTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.client = CredentialClientInstance.objects.create(
            application=self.application,
            instance_id='cycle-sdk', type='sdk', event_receipts_supported=True,
            date_last_seen=timezone.now(),
        )
        CredentialRotationEvent.objects.all().delete()

    def subscription(self):
        self.credential.mode = self.credential.Mode.subscription
        self.credential.save(update_fields=['mode'])
        self.credential.subscription_accounts.add(self.primary, self.backup)

    def change(self, account=None, status=None):
        account = account or self.primary
        execution = AutomationExecution.objects.create(snapshot={}, org_id=self.org.id)
        change = ChangeSecretRecord.objects.create(
            account=account, asset=self.asset, execution=execution,
            old_secret=account.secret, new_secret=f'new-{uuid4()}',
        )
        if status:
            if status == 'success':
                account.secret = change.new_secret
                account.save()
            change.status = status
            change.save(update_fields=['status'])
        return change

    def test_subscription_success_is_one_complete_cycle(self):
        self.subscription()
        change = self.change(status='success')
        result = cycle_directory(self.credential)
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['results'][0]['id'], str(change.id))
        detail = cycle_detail(self.credential, change.id)
        self.assertEqual(detail['kind'], 'subscription')
        self.assertEqual(detail['status'], 'success')
        self.assertEqual(detail['account']['id'], str(self.primary.id))
        self.assertEqual([event['event'] for event in detail['events']], [
            'credential.change.started', 'credential.change.completed', 'credential.updated',
        ])
        self.assertTrue(all(not event['requires_confirmation'] for event in detail['events']))

    def test_concurrent_accounts_and_failed_attempts_are_separate_cycles(self):
        self.subscription()
        first = self.change()
        second = self.change(account=self.backup, status='failed')
        retry = self.change(status='success')
        self.assertEqual(cycle_directory(self.credential)['count'], 3)
        pending = cycle_detail(self.credential, first.id)
        failed = cycle_detail(self.credential, second.id)
        succeeded = cycle_detail(self.credential, retry.id)
        self.assertEqual(pending['status'], 'running')
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['event_count'], 2)
        self.assertEqual(succeeded['status'], 'success')
        self.assertNotIn('credential.updated', [event['event'] for event in failed['events']])

    def test_direct_updates_do_not_merge_by_date_or_revision(self):
        self.subscription()
        self.primary.secret = 'first-direct-update'
        self.primary.save()
        self.primary.secret = 'second-direct-update'
        self.primary.save()
        rows = cycle_directory(self.credential)['results']
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]['id'], rows[1]['id'])
        self.assertTrue(all(row['kind'] == 'update' and row['event_count'] == 1 for row in rows))

    def test_scope_excludes_application_wide_and_other_policy_events(self):
        self.subscription()
        change = self.change()
        global_event = record(AuditEvent.CONFIGURATION_UPDATED, application=self.application)
        enqueue(global_event, ApplicationEvent.CONFIGURATION_UPDATED)
        other = ApplicationCredential.objects.create(name='Other subscription', mode='subscription')
        CredentialApplicationBinding.objects.create(credential=other, application=self.application)
        foreign = record(AuditEvent.CREDENTIAL_PUBLISHED, credential=other)
        enqueue(foreign, ApplicationEvent.CREDENTIAL_UPDATED)
        self.assertEqual(cycle_directory(self.credential)['count'], 1)
        self.assertEqual(cycle_detail(self.credential, change.id)['event_count'], 1)
        self.credential.org_id = uuid4()
        self.assertEqual(cycle_directory(self.credential)['count'], 0)

    def test_queue_and_running_emit_one_change_start_in_the_same_cycle(self):
        self.subscription()
        change = self.change()
        change.status = 'running'
        change.save(update_fields=['status'])
        detail = cycle_detail(self.credential, change.id)
        self.assertEqual(detail['event_count'], 1)
        self.assertEqual(detail['events'][0]['event'], 'credential.change.started')

    def test_cycles_without_clients_still_include_emitted_events(self):
        self.subscription()
        self.client.delete()
        CredentialRotationEvent.objects.all().delete()
        change = self.change(status='failed')
        detail = cycle_detail(self.credential, change.id)
        self.assertEqual(detail['event_count'], 2)
        self.assertTrue(all(event['recipient_count'] == 0 for event in detail['events']))

    def test_rotation_cycles_paginate_without_splitting_their_events(self):
        manager = CredentialRotationManager(self.credential.id)
        manager.start()
        self.credential.refresh_from_db()
        first = self.credential.rotation_records.first()
        manager._finish(self.credential, first, 'success')
        manager.start()
        second = self.credential.rotation_records.first()
        latest = cycle_directory(self.credential, 1, 0)
        older = cycle_directory(self.credential, 1, 1)
        self.assertEqual(latest['count'], 2)
        self.assertEqual(latest['results'][0]['id'], str(second.id))
        self.assertEqual(older['results'][0]['id'], str(first.id))
        self.assertEqual(cycle_detail(self.credential, first.id)['event_count'], 4)
        self.assertIsNone(cycle_detail(self.credential, first.id)['preparation'])

    def test_event_receipt_is_separate_from_application_confirmation(self):
        manager = CredentialRotationManager(self.credential.id)
        manager.start()
        self.credential.refresh_from_db()
        rotation = self.credential.rotation_records.first()
        event = rotation.events.first()
        receive(self.client.id, self.org.id, event.source_event_id)
        detail = cycle_detail(self.credential, rotation.id)
        self.assertEqual(detail['events'][0]['received_count'], 1)
        self.assertEqual(detail['events'][0]['confirmed_count'], 0)
        client_manager = CredentialClientManager(self.application, instance_id=self.client.instance_id)
        client_manager.fetch(self.credential.key, '127.0.0.1')
        client_manager.confirm(self.credential.key, self.credential.revision, self.credential.active_account_id)
        detail = cycle_detail(self.credential, rotation.id)
        self.assertEqual(detail['events'][0]['confirmed_count'], 1)
        self.assertIsNotNone(detail['events'][0]['recipients'][0]['confirmed_at'])
        self.assertTrue(all(not event['requires_confirmation'] for event in detail['events'][1:]))

    def test_sdk_and_agent_with_same_instance_id_confirm_independently(self):
        agent = CredentialClientInstance.objects.create(
            application=self.application, instance_id=self.client.instance_id, type='agent',
        )
        CredentialRotationManager(self.credential.id).start()
        self.credential.refresh_from_db()
        rotation = self.credential.rotation_records.first()
        sdk = CredentialClientManager(self.application, instance_id=self.client.instance_id)
        sdk.fetch(self.credential.key, '127.0.0.1')
        sdk.confirm(self.credential.key, self.credential.revision, self.credential.active_account_id)
        recipients = cycle_detail(self.credential, rotation.id)['events'][0]['recipients']
        self.assertIsNotNone(next(row for row in recipients if row['type'] == 'sdk')['confirmed_at'])
        self.assertIsNone(next(row for row in recipients if row['type'] == 'agent')['confirmed_at'])
        agent_manager = CredentialClientManager(agent)
        agent_manager.fetch(self.credential.key, '127.0.0.1')
        agent_manager.confirm(self.credential.key, self.credential.revision, self.credential.active_account_id)
        recipients = cycle_detail(self.credential, rotation.id)['events'][0]['recipients']
        self.assertTrue(all(row['confirmed_at'] for row in recipients))

    def test_historical_confirmation_and_receipt_survive_client_deletion_and_later_rotation(self):
        manager = CredentialRotationManager(self.credential.id)
        manager.start()
        self.credential.refresh_from_db()
        first = self.credential.rotation_records.first()
        client_manager = CredentialClientManager(self.application, instance_id=self.client.instance_id)
        client_manager.fetch(self.credential.key, '127.0.0.1')
        client_manager.confirm(self.credential.key, self.credential.revision, self.credential.active_account_id)
        receive(self.client.id, self.org.id, first.events.first().source_event_id)
        manager._finish(self.credential, first, 'success')
        manager.start()
        second = self.credential.rotation_records.first()
        self.client.delete()
        old = cycle_detail(self.credential, first.id)['events'][0]
        current = cycle_detail(self.credential, second.id)['events'][0]
        self.assertEqual(old['confirmed_count'], 1)
        self.assertEqual(old['received_count'], 1)
        self.assertFalse(old['recipients'][0]['is_active'])
        self.assertEqual(current['confirmed_count'], 0)

    def test_stale_audit_rotation_does_not_absorb_standalone_grants(self):
        manager = CredentialRotationManager(self.credential.id)
        manager.start()
        self.credential.refresh_from_db()
        rotation = self.credential.rotation_records.first()
        manager._finish(self.credential, rotation, 'success')
        grant = record(AuditEvent.AUTHORIZATION_GRANTED, credential=self.credential)
        enqueue(grant, ApplicationEvent.CREDENTIAL_UPDATED)
        self.assertEqual(cycle_directory(self.credential)['count'], 2)
        detail = cycle_detail(self.credential, grant.id)
        self.assertEqual(detail['kind'], 'event')
        self.assertIsNone(detail['rotation_id'])

    def test_existing_revision_confirmation_is_valid_for_a_later_grant(self):
        manager = CredentialRotationManager(self.credential.id)
        manager.start()
        self.credential.refresh_from_db()
        rotation = self.credential.rotation_records.first()
        client_manager = CredentialClientManager(self.application, instance_id=self.client.instance_id)
        client_manager.fetch(self.credential.key, '127.0.0.1')
        client_manager.confirm(self.credential.key, self.credential.revision, self.credential.active_account_id)
        manager._finish(self.credential, rotation, 'success')
        grant = record(AuditEvent.AUTHORIZATION_GRANTED, credential=self.credential)
        enqueue(grant, ApplicationEvent.CREDENTIAL_UPDATED)
        detail = cycle_detail(self.credential, grant.id)
        self.assertEqual(detail['events'][0]['confirmed_count'], 1)
        self.assertEqual(detail['events'][0]['received_count'], 0)

    def test_historical_rotation_keeps_application_confirmation_after_mode_change(self):
        manager = CredentialRotationManager(self.credential.id)
        manager.start()
        self.credential.refresh_from_db()
        rotation = self.credential.rotation_records.first()
        client_manager = CredentialClientManager(self.application, instance_id=self.client.instance_id)
        client_manager.fetch(self.credential.key, '127.0.0.1')
        client_manager.confirm(self.credential.key, self.credential.revision, self.credential.active_account_id)
        manager._finish(self.credential, rotation, 'success')
        self.credential.mode = 'subscription'
        self.credential.save(update_fields=['mode'])
        detail = cycle_detail(self.credential, rotation.id)
        self.assertTrue(detail['events'][0]['requires_confirmation'])
        self.assertEqual(detail['events'][0]['confirmed_count'], 1)

    def test_api_validates_cycle_scope_and_does_not_expose_secrets(self):
        self.subscription()
        change = self.change(status='success')
        view = ApplicationCredentialViewSet.as_view({'get': 'event_cycles'})
        for params, expected in [({'cycle_id': 'bad'}, 400), ({'cycle_id': str(uuid4())}, 404),
                                 ({'limit': 101}, 400), ({'cycle_id': str(change.id)}, 200)]:
            with transaction.atomic():
                response = view(self.request('get', '/event-cycles/', params), pk=self.credential.id)
            self.assertEqual(response.status_code, expected)
            self.assertNotIn('primary-secret', str(response.data))
            self.assertNotIn(change.new_secret, str(response.data))

    def test_websocket_lifecycle_and_update_share_operation_id(self):
        self.subscription()
        change = self.change(status='success')
        layer = Mock(group_send=AsyncMock())
        with patch('accounts.credential_client.events.get_channel_layer', return_value=layer):
            for event in CredentialRotationEvent.objects.filter(cycle_id=change.id):
                _publish_stream(event.source_event_id, event.event)
        self.assertTrue(layer.group_send.await_args_list)
        self.assertTrue(all(call.args[1]['payload']['operation_id'] == str(change.id)
                            for call in layer.group_send.await_args_list))

    def test_legacy_lifecycle_events_remain_visible_without_invented_cycles(self):
        self.subscription()
        audit = record(AuditEvent.SECRET_CHANGE_STARTED, credential=self.credential)
        enqueue(audit, ApplicationEvent.CREDENTIAL_CHANGE_STARTED)
        CredentialRotationEvent.objects.filter(source_event_id=audit.id).update(cycle_id=None)
        detail = cycle_detail(self.credential, audit.id)
        self.assertEqual(detail['kind'], 'legacy')
        self.assertEqual(detail['event_count'], 1)
