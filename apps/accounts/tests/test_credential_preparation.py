"""The source-account fetch window begins only after the backup is published."""
from datetime import timedelta
from unittest.mock import patch

from django.db import transaction
from django.utils import timezone

from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.api.account.credential import ApplicationCredentialViewSet
from accounts.credential_client.manager import CredentialClientManager
from accounts.credential_rotation import CredentialRotationManager, preflight
from accounts.credential_rotation.cycles import cycle_detail
from accounts.credential_rotation.execution import execute
from accounts.credential_rotation.preparation import record_secret_access
from accounts.credential_rotation.source_traffic import info as source_traffic_info
from accounts.models import Account, ChangeSecretAutomation, CredentialClientInstance
from accounts.serializers import ApplicationCredentialSerializer
from accounts.tests.base import CredentialTestCase
from common.exceptions import JMSException


class CredentialSourceTrafficTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.manager = CredentialRotationManager(self.credential.id)
        self.started = timezone.now()
        self.credential.source_no_traffic_days = 1
        self.credential.save(update_fields=['source_no_traffic_days'])

    def legacy_fetch(self, account):
        view = IntegrationApplicationViewSet.as_view({'get': 'get_account_secret'})
        return view(self.request('get', '/', {'account_id': str(account.id)}, user=self.application))

    def start_switch(self):
        with patch('accounts.credential_rotation.manager.timezone.now', return_value=self.started):
            self.manager.start(self.admin.name, self.admin.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.active_account_id, self.backup.id)
        self.assertEqual(self.credential.status, 'waiting_switch')
        return self.credential.rotation_records.first()

    def test_new_duration_name_and_legacy_alias(self):
        self.assertEqual(self.credential._meta.get_field('source_no_traffic_days').default, 7)
        for value in (0, -1, 3651, 1.5):
            serializer = ApplicationCredentialSerializer(
                self.credential, data={'source_no_traffic_days': value}, partial=True,
            )
            self.assertFalse(serializer.is_valid(), value)
        serializer = ApplicationCredentialSerializer(
            self.credential, data={'standby_no_traffic_days': 14}, partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.save().source_no_traffic_days, 14)
        self.assertEqual(serializer.data['source_no_traffic_days'], 14)
        self.assertEqual(serializer.data['standby_no_traffic_days'], 14)

    def test_switch_has_no_prior_alignment_or_backup_idle_gate(self):
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            self.assertEqual(self.legacy_fetch(self.backup).status_code, 200)
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
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=access_at):
            self.assertEqual(self.legacy_fetch(self.primary).status_code, 200)
        with patch('accounts.credential_rotation.source_traffic.timezone.now',
                   return_value=self.started + timedelta(days=1)):
            _, blockers = self.manager.check_usage()
        self.assertEqual(blockers[0]['reason'], 'source_secret_access')
        self.assertEqual(blockers[0]['source_traffic']['eligible_at'],
                         (access_at + timedelta(days=1)).isoformat())
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=access_at + timedelta(hours=1)):
            self.assertEqual(self.legacy_fetch(self.backup).status_code, 200)
        with patch('accounts.credential_rotation.source_traffic.timezone.now',
                   return_value=access_at + timedelta(days=1)):
            _, blockers = self.manager.check_usage()
        self.assertEqual(blockers, [])
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'ready_for_change')
        self.assertIn('rotation.source.ready', [event['event'] for event in cycle_detail(
            self.credential, rotation.id,
        )['events']])

    def test_legacy_source_user_must_fetch_backup_after_switch(self):
        with patch('accounts.credential_rotation.preparation.timezone.now',
                   return_value=self.started - timedelta(seconds=1)):
            self.assertEqual(self.legacy_fetch(self.primary).status_code, 200)
        rotation = self.start_switch()
        self.assertEqual(
            rotation.participant_snapshot['legacy_applications'][0]['id'],
            str(self.application.id),
        )
        with patch('accounts.credential_rotation.source_traffic.timezone.now',
                   return_value=self.started + timedelta(days=1)):
            _, blockers = self.manager.check_usage()
        self.assertEqual(blockers[0]['reason'], 'using_source')
        with patch('accounts.credential_rotation.preparation.timezone.now',
                   return_value=self.started + timedelta(hours=1)):
            self.assertEqual(self.legacy_fetch(self.backup).status_code, 200)
        with patch('accounts.credential_rotation.source_traffic.timezone.now',
                   return_value=self.started + timedelta(days=1)):
            self.assertEqual(self.manager.check_usage()[1], [])

    def test_stale_account_edits_preserve_latest_source_fetch(self):
        self.start_switch()
        stale = Account.objects.get(pk=self.primary.pk)
        fetched_at = self.started + timedelta(hours=1)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=fetched_at):
            self.assertEqual(self.legacy_fetch(self.primary).status_code, 200)
        stale.comment = 'Updated from an older account object'
        stale.save()
        self.primary.refresh_from_db()
        self.assertEqual(self.primary.date_last_secret_access, fetched_at)

    def test_late_source_fetch_revokes_readiness(self):
        self.start_switch()
        ready_at = self.started + timedelta(days=1)
        with patch('accounts.credential_rotation.source_traffic.timezone.now', return_value=ready_at):
            self.assertEqual(self.manager.check_usage()[1], [])
        with patch('accounts.credential_rotation.preparation.timezone.now',
                   return_value=ready_at + timedelta(seconds=1)):
            self.assertEqual(self.legacy_fetch(self.primary).status_code, 200)
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

    def test_direct_source_fetch_is_denied_during_secret_change(self):
        self.start_switch()
        previous = self.primary.date_last_secret_access
        self.credential.status = self.credential.Status.changing_secret
        self.credential.save(update_fields=['status'])
        with transaction.atomic():
            with self.assertRaises(JMSException):
                record_secret_access(self.primary, self.application)
        with transaction.atomic():
            self.assertNotEqual(self.legacy_fetch(self.primary).status_code, 200)
        direct = CredentialClientManager(self.application, instance_id='direct-source-sdk')
        with transaction.atomic():
            with self.assertRaises(JMSException):
                direct.fetch('', '127.0.0.1', self.primary.id)
        self.primary.refresh_from_db()
        self.assertEqual(self.primary.date_last_secret_access, previous)
        self.assertEqual(self.legacy_fetch(self.backup).status_code, 200)

    def test_execution_rechecks_source_fetches_under_policy_lock(self):
        self.started -= timedelta(days=2)
        rotation = self.start_switch()
        self.assertEqual(self.manager.check_usage()[1], [])
        self.assertEqual(self.legacy_fetch(self.primary).status_code, 200)
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
            self.assertIn('rotation.verification.started', [event['event'] for event in cycle_detail(
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
        self.assertIn('rotation.verification.started', [event['event'] for event in cycle_detail(
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
