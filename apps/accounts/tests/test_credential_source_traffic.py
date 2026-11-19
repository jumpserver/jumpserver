"""The source-account fetch window begins after all clients confirm switching."""
from datetime import timedelta
from unittest.mock import patch

from django.db import transaction
from django.utils import timezone

from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.api.account.credential import ApplicationCredentialViewSet, CredentialClientViewSet
from accounts.credential_client.manager import CredentialClientManager
from accounts.credential_rotation import CredentialRotationManager, preflight
from accounts.credential_rotation.cycles import cycle_detail
from accounts.credential_rotation.execution import execute
from accounts.credential_rotation.source_traffic import record_secret_access
from accounts.credential_rotation.source_traffic import info as source_traffic_info
from accounts.models import Account, ChangeSecretAutomation, CredentialClientInstance
from accounts.serializers import ApplicationCredentialListSerializer, ApplicationCredentialSerializer
from accounts.tests.base import CredentialTestCase
from common.exceptions import JMSException


class CredentialSourceTrafficTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.manager = CredentialRotationManager(self.credential.id)
        self.started = timezone.now()
        self.credential.source_no_traffic_minutes = 1440
        self.credential.save(update_fields=['source_no_traffic_minutes'])

    def fetch_account(self, account):
        view = CredentialClientViewSet.as_view({'get': 'credential'})
        return view(self.request('get', '/', {'account_id': str(account.id), 'instance_id': 'source-observer'}, user=self.application))

    def start_switch(self):
        with patch('accounts.credential_rotation.manager.timezone.now', return_value=self.started):
            self.manager.start(self.admin.name, self.admin.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.active_account_id, self.backup.id)
        self.assertEqual(self.credential.status, 'waiting_switch')
        return self.credential.rotation_records.first()

    def test_source_observation_duration_validation(self):
        self.assertEqual(self.credential._meta.get_field('source_no_traffic_minutes').default, 10080)
        for value in (0, -1, 1.5, 5256001):
            serializer = ApplicationCredentialSerializer(
                self.credential, data={'source_no_traffic_minutes': value}, partial=True,
            )
            self.assertFalse(serializer.is_valid(), value)
        for value in (1, 1440, 5256000):
            serializer = ApplicationCredentialSerializer(
                self.credential, data={'source_no_traffic_minutes': value}, partial=True,
            )
            self.assertTrue(serializer.is_valid(), serializer.errors)
            serializer.save()
            self.credential.refresh_from_db()
            self.assertEqual(self.credential.source_no_traffic_minutes, value)
            self.assertEqual(serializer.data['source_no_traffic_minutes'], value)

    def test_legacy_api_duration_is_converted_from_days(self):
        serializer = ApplicationCredentialSerializer(
            self.credential, data={'source_no_traffic_days': 3}, partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.save().source_no_traffic_minutes, 4320)
        self.assertEqual(serializer.data['source_no_traffic_days'], 3)

    def test_one_minute_source_observation_restarts_after_fetch(self):
        self.credential.source_no_traffic_minutes = 1
        self.credential.save(update_fields=['source_no_traffic_minutes'])
        rotation = self.start_switch()
        self.assertEqual(rotation.participant_snapshot['source_traffic']['no_traffic_minutes'], 1)
        access_at = self.started + timedelta(seconds=30)
        with patch('accounts.credential_rotation.source_traffic.timezone.now', return_value=access_at):
            self.assertEqual(self.fetch_account(self.primary).status_code, 200)
        ready_at = access_at + timedelta(minutes=1)
        with patch('accounts.credential_rotation.source_traffic.timezone.now',
                   return_value=ready_at - timedelta(microseconds=1)):
            _, blockers = self.manager.check_usage()
        self.assertEqual(blockers[0]['source_traffic']['eligible_at'], ready_at.isoformat())
        with patch('accounts.credential_rotation.source_traffic.timezone.now', return_value=ready_at):
            self.assertEqual(self.manager.check_usage()[1], [])

    def test_legacy_day_snapshots_are_returned_in_minutes(self):
        rotation = self.start_switch()
        traffic = rotation.participant_snapshot['source_traffic']
        event_id, event_traffic = next(iter(traffic['event_observations'].items()))
        for observation in (traffic, event_traffic):
            observation.pop('no_traffic_minutes')
            observation['no_traffic_days'] = 2
        rotation.save(update_fields=['participant_snapshot'])
        detail = cycle_detail(self.credential, rotation.id)
        self.assertEqual(detail['source_traffic']['no_traffic_minutes'], 2880)
        self.assertEqual(detail['source_traffic']['eligible_at'], (self.started + timedelta(days=2)).isoformat())
        event = next(event for event in detail['events'] if event['id'] == event_id)
        self.assertEqual(event['source_traffic']['no_traffic_minutes'], 2880)

    def test_switch_has_no_prior_alignment_or_backup_idle_gate(self):
        with patch('accounts.credential_rotation.source_traffic.timezone.now', return_value=self.started):
            self.assertEqual(self.fetch_account(self.backup).status_code, 200)
        rotation = self.start_switch()
        self.assertEqual(rotation.source_account_id, self.primary.id)
        self.assertEqual(rotation.target_account_id, self.backup.id)
        self.assertNotIn('preparation', rotation.participant_snapshot)
        self.assertEqual(rotation.participant_snapshot['source_traffic']['started_at'], self.started.isoformat())
        self.assertEqual(source_traffic_info(self.credential, rotation)['eligible_at'],
                         (self.started + timedelta(days=1)).isoformat())
        detail = cycle_detail(self.credential, rotation.id)
        waiting = next(event for event in detail['events'] if event['event'] == 'rotation.source.waiting')
        self.assertEqual(waiting['source_traffic']['eligible_at'],
                         (self.started + timedelta(days=1)).isoformat())

    def test_source_fetch_resets_window_but_backup_fetch_does_not(self):
        rotation = self.start_switch()
        access_at = self.started + timedelta(hours=12)
        with patch('accounts.credential_rotation.source_traffic.timezone.now', return_value=access_at):
            self.assertEqual(self.fetch_account(self.primary).status_code, 200)
        with patch('accounts.credential_rotation.source_traffic.timezone.now',
                   return_value=self.started + timedelta(days=1)):
            _, blockers = self.manager.check_usage()
        self.assertEqual(blockers[0]['reason'], 'source_secret_access')
        self.assertEqual(blockers[0]['source_traffic']['eligible_at'],
                         (access_at + timedelta(days=1)).isoformat())
        with patch('accounts.credential_rotation.source_traffic.timezone.now', return_value=access_at + timedelta(hours=1)):
            self.assertEqual(self.fetch_account(self.backup).status_code, 200)
        with patch('accounts.credential_rotation.source_traffic.timezone.now',
                   return_value=access_at + timedelta(days=1)):
            _, blockers = self.manager.check_usage()
        self.assertEqual(blockers, [])
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'ready_for_change')
        self.assertIn('rotation.source.ready', [event['event'] for event in cycle_detail(
            self.credential, rotation.id,
        )['events']])


    def test_stale_account_edits_preserve_latest_source_fetch(self):
        self.start_switch()
        stale = Account.objects.get(pk=self.primary.pk)
        fetched_at = self.started + timedelta(hours=1)
        with patch('accounts.credential_rotation.source_traffic.timezone.now', return_value=fetched_at):
            self.assertEqual(self.fetch_account(self.primary).status_code, 200)
        stale.comment = 'Updated from an older account object'
        stale.save()
        self.primary.refresh_from_db()
        self.assertEqual(self.primary.date_last_secret_access, fetched_at)

    def test_late_source_fetch_revokes_readiness(self):
        self.start_switch()
        ready_at = self.started + timedelta(days=1)
        with patch('accounts.credential_rotation.source_traffic.timezone.now', return_value=ready_at):
            self.assertEqual(self.manager.check_usage()[1], [])
        with patch('accounts.credential_rotation.source_traffic.timezone.now',
                   return_value=ready_at + timedelta(seconds=1)):
            self.assertEqual(self.fetch_account(self.primary).status_code, 200)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_switch')
        with self.assertRaises(JMSException):
            self.manager.change_secret()

        # A stale ready state must not bypass the final source fetch check.
        self.credential.status = self.credential.Status.ready_for_change
        self.credential.save(update_fields=['status'])
        with self.assertRaisesMessage(JMSException, 'source account'):
            self.manager.change_secret()

    def test_confirmed_client_and_source_window_are_both_required(self):
        client = CredentialClientManager(self.application, instance_id='source-window-sdk')
        fetched = client.fetch(self.credential.key, '127.0.0.1')
        client.confirm(self.credential.key, fetched['revision'], self.primary.id)
        CredentialClientInstance.objects.filter(pk=client.client.pk).update(date_last_seen=timezone.now())
        self.start_switch()
        fetched = client.fetch(self.credential.key, '127.0.0.1')
        client.confirm(self.credential.key, fetched['revision'], self.backup.id)
        CredentialClientInstance.objects.filter(pk=client.client.pk).update(date_last_seen=timezone.now())
        self.assertEqual(self.manager.check_usage()[1][0]['reason'], 'source_secret_access')

    def test_display_phase_follows_client_switch_and_source_observation(self):
        from accounts.credential_rotation.participants import build

        client = CredentialClientManager(self.application, instance_id='phase-sdk')
        CredentialClientInstance.objects.filter(pk=client.client.pk).update(date_last_seen=timezone.now())
        fetched = client.fetch(self.credential.key, '127.0.0.1')
        client.confirm(self.credential.key, fetched['revision'], self.primary.id)
        self.start_switch()

        def assert_phase(expected):
            self.credential.refresh_from_db()
            self.assertEqual(build(self.credential)['rotation_phase'], expected)
            detail = cycle_detail(self.credential, self.credential.rotation_records.first().id)
            self.assertEqual(detail['rotation_status']['rotation_phase'], expected)
            self.assertEqual(detail['rotation_status']['credential_status'], self.credential.status)
            for serializer in (ApplicationCredentialSerializer, ApplicationCredentialListSerializer):
                data = serializer(self.credential).data
                self.assertEqual(data['rotation_phase'], expected)
                self.assertEqual(data['status']['value'], self.credential.status)

        assert_phase('waiting_switch')
        self.assertIsNone(source_traffic_info(self.credential))
        self.assertNotIn('rotation.source.waiting', [event['event'] for event in cycle_detail(
            self.credential, self.credential.rotation_records.first().id,
        )['events']])
        fetched = client.fetch(self.credential.key, '127.0.0.1')
        client.confirm(self.credential.key, fetched['revision'], self.backup.id)
        CredentialClientInstance.objects.filter(pk=client.client.pk).update(date_last_seen=timezone.now())
        assert_phase('waiting_source')
        self.assertEqual(self.credential.status, 'waiting_switch')
        self.assertEqual(self.manager.check_usage()[1][0]['reason'], 'source_secret_access')

        with patch('accounts.credential_rotation.source_traffic.timezone.now',
                   return_value=self.started + timedelta(days=1, seconds=1)):
            # Readiness still requires the participant to be online.
            CredentialClientInstance.objects.filter(pk=client.client.pk).update(
                date_last_seen=self.started + timedelta(days=1, seconds=1),
            )
            self.assertEqual(self.manager.check_usage()[1], [])
            assert_phase('ready_for_change')

        record_secret_access(self.primary)
        assert_phase('waiting_source')
        CredentialClientInstance.objects.filter(pk=client.client.pk).update(
            date_last_seen=self.started - timedelta(minutes=3),
        )
        assert_phase('waiting_switch')

    def test_receipts_and_partial_confirmation_do_not_start_the_observation_window(self):
        from accounts.credential_rotation.events import receive

        clients = [CredentialClientManager(self.application, instance_id=f'wait-client-{i}') for i in range(2)]
        for client in clients:
            client.fetch(self.credential.key, '127.0.0.1')
        rotation = self.start_switch()
        publication = rotation.events.get(event='credential.switch.published')
        for client in clients:
            receive(client.client.id, self.org.id, publication.source_event_id)
        self.assertIsNone(source_traffic_info(self.credential))
        self.assertFalse(rotation.events.filter(event='rotation.source.waiting').exists())

        first_confirmation = self.started + timedelta(days=2)
        with patch('accounts.credential_rotation.source_traffic.timezone.now', return_value=first_confirmation):
            fetched = clients[0].fetch(self.credential.key, '127.0.0.1')
            clients[0].confirm(self.credential.key, fetched['revision'], self.backup.id)
            self.assertIsNone(source_traffic_info(self.credential))
            self.assertTrue(self.manager.check_usage()[1])
        self.assertFalse(rotation.events.filter(event='rotation.source.waiting').exists())

        confirmed_at = self.started + timedelta(days=3)
        with patch('accounts.credential_rotation.source_traffic.timezone.now', return_value=confirmed_at):
            CredentialClientInstance.objects.filter(pk__in=[client.client.pk for client in clients]).update(
                date_last_seen=confirmed_at,
            )
            fetched = clients[1].fetch(self.credential.key, '127.0.0.1')
            clients[1].confirm(self.credential.key, fetched['revision'], self.backup.id)
            traffic = source_traffic_info(self.credential)
            self.assertEqual(traffic['started_at'], confirmed_at.isoformat())
            self.assertEqual(traffic['eligible_at'], (confirmed_at + timedelta(days=1)).isoformat())
            self.assertEqual(traffic['remaining_seconds'], 86400)
            clients[1].confirm(self.credential.key, fetched['revision'], self.backup.id)
            self.assertEqual(rotation.events.filter(event='rotation.source.waiting').count(), 1)
            self.assertEqual(self.manager.check_usage()[1][0]['reason'], 'source_secret_access')

    def test_legacy_open_observation_restarts_after_application_confirmation(self):
        client = CredentialClientManager(self.application, instance_id='legacy-observer')
        client.fetch(self.credential.key, '127.0.0.1')
        rotation = self.start_switch()
        rotation.refresh_from_db()
        rotation.participant_snapshot['source_traffic']['started_at'] = self.started.isoformat()
        rotation.save(update_fields=['participant_snapshot'])
        confirmed_at = self.started + timedelta(days=3)
        with patch('accounts.credential_rotation.source_traffic.timezone.now', return_value=confirmed_at):
            self.assertIsNone(source_traffic_info(self.credential))
            self.assertTrue(self.manager.check_usage()[1])
            CredentialClientInstance.objects.filter(pk=client.client.pk).update(date_last_seen=confirmed_at)
            fetched = client.fetch(self.credential.key, '127.0.0.1')
            client.confirm(self.credential.key, fetched['revision'], self.backup.id)
            traffic = source_traffic_info(self.credential)
            self.assertEqual(traffic['started_at'], confirmed_at.isoformat())
            self.assertFalse(traffic['ready'])

    def test_finished_cycle_does_not_use_live_progress_from_another_cycle(self):
        rotation = self.start_switch()
        self.manager.cancel()
        self.assertEqual(self.manager.complete()[1], [])
        self.manager.start()
        self.credential.refresh_from_db()
        self.assertIsNone(cycle_detail(self.credential, rotation.id)['rotation_status'])

    def test_direct_source_fetch_is_denied_during_secret_change(self):
        self.start_switch()
        previous = self.primary.date_last_secret_access
        self.credential.status = self.credential.Status.changing_secret
        self.credential.save(update_fields=['status'])
        with transaction.atomic():
            with self.assertRaises(JMSException):
                record_secret_access(self.primary)
        with transaction.atomic():
            self.assertNotEqual(self.fetch_account(self.primary).status_code, 200)
        direct = CredentialClientManager(self.application, instance_id='direct-source-sdk')
        with transaction.atomic():
            with self.assertRaises(JMSException):
                direct.fetch('', '127.0.0.1', self.primary.id)
        self.primary.refresh_from_db()
        self.assertEqual(self.primary.date_last_secret_access, previous)
        self.assertEqual(self.fetch_account(self.backup).status_code, 200)

    def test_execution_rechecks_source_fetches_under_policy_lock(self):
        self.started -= timedelta(days=2)
        rotation = self.start_switch()
        self.assertEqual(self.manager.check_usage()[1], [])
        self.assertEqual(self.fetch_account(self.primary).status_code, 200)
        self.credential.status = self.credential.Status.ready_for_change
        self.credential.save(update_fields=['status'])
        automation = ChangeSecretAutomation.objects.create(
            name=f'Source window test {rotation.id}', accounts=[self.primary.username],
            secret_type=self.primary.secret_type, secret_strategy='random',
            check_conn_after_change=True, is_periodic=False,
        )
        automation.assets.add(self.asset)
        rotation.change_automation = automation
        rotation.save(update_fields=['change_automation'])
        with self.assertRaisesMessage(JMSException, 'source account'):
            execute(rotation.id)

    def test_real_preflight_publishes_after_backup_verification_without_idle_wait(self):
        self.precheck_patch.stop()
        with patch('accounts.credential_rotation.preflight.dispatch'):
            self.manager.start(self.admin.name, self.admin.id)
            self.credential.refresh_from_db()
            self.assertEqual(self.credential.active_account_id, self.primary.id)
            execution = preflight.latest(self.credential)
            rotation = self.credential.rotation_records.first()
            self.assertEqual(rotation.status, 'preparing')
            self.assertIn('rotation.verify.started', [event['event'] for event in cycle_detail(
                self.credential, rotation.id,
            )['events']])
            execution.status = 'success'
            execution.summary = {'ok_assets': 1, 'fail_assets': 0, 'error_assets': 0}
            execution.date_finished = timezone.now()
            execution.save()
            preflight.finish(execution.id)
        self.credential.refresh_from_db()
        rotation.refresh_from_db()
        self.assertEqual(self.credential.active_account_id, self.backup.id)
        self.assertEqual(rotation.status, 'running')

    def test_start_cycle_returns_traceable_id_during_verification(self):
        self.precheck_patch.stop()
        view = ApplicationCredentialViewSet.as_view({'post': 'start_cycle'})
        with patch('accounts.credential_rotation.preflight.dispatch'):
            response = view(self.request('post', '/'), pk=self.credential.id)
        self.assertEqual(response.status_code, 201)
        rotation = self.credential.rotation_records.get()
        self.assertEqual(response.data['cycle_id'], str(rotation.id))
        self.assertEqual(rotation.status, 'preparing')
        self.assertIn('rotation.verify.started', [event['event'] for event in cycle_detail(
            self.credential, rotation.id,
        )['events']])

    def test_preflight_failure_does_not_switch_account(self):
        self.precheck_patch.stop()
        with patch('accounts.credential_rotation.preflight.dispatch'):
            self.manager.start(self.admin.name, self.admin.id)
            execution = preflight.latest(self.credential)
            preflight.fail(execution.id, 'failed')
        self.credential.refresh_from_db()
        rotation = self.credential.rotation_records.first()
        self.assertEqual(self.credential.active_account_id, self.primary.id)
        self.assertEqual(self.credential.status, 'idle')
        self.assertEqual(rotation.status, 'failed')

    def test_preflight_can_be_cancelled_before_switch(self):
        self.precheck_patch.stop()
        with patch('accounts.credential_rotation.preflight.dispatch'):
            self.manager.start(self.admin.name, self.admin.id)
            self.manager.cancel('Operator stopped the cycle.')
        self.credential.refresh_from_db()
        rotation = self.credential.rotation_records.first()
        self.assertEqual(self.credential.active_account_id, self.primary.id)
        self.assertEqual(rotation.status, 'cancelled')

    def test_check_usage_api_exposes_source_observation(self):
        self.start_switch()
        view = ApplicationCredentialViewSet.as_view({'post': 'check_usage'})
        response = view(self.request('post', '/'), pk=self.credential.id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['blockers'][0]['reason'], 'source_secret_access')
        self.assertEqual(response.data['rotation_status']['source_traffic']['source_account_id'],
                         str(self.primary.id))
