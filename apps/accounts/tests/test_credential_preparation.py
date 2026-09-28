from datetime import timedelta
from unittest.mock import PropertyMock, patch

from django.test import override_settings
from django.utils import timezone

from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.credential_client.manager import CredentialClientManager
from accounts.credential_rotation import CredentialRotationManager, preparation
from accounts.credential_rotation.cycles import cycle_detail
from accounts.models import (
    Account, ClientAccessConfiguration, CredentialClientInstance,
    CredentialApplicationBinding, IntegrationApplication,
)
from accounts.serializers import ApplicationCredentialSerializer
from accounts.tests.base import CredentialTestCase
from common.exceptions import JMSException


class CredentialPreparationTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.preparation_patch.stop()
        self.manager = CredentialRotationManager(self.credential.id)
        self.started = timezone.now()

    def legacy_fetch(self, account):
        view = IntegrationApplicationViewSet.as_view({'get': 'get_account_secret'})
        return view(self.request('get', '/', {'account_id': str(account.id)}, user=self.application))

    def prepare_legacy(self):
        self.manager.prepare(self.admin.name, self.admin.id)
        self.assertEqual(self.legacy_fetch(self.primary).status_code, 200)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_standby')
        self.rotation_id = self.credential.rotation_records.first().id

    def test_default_seven_days_and_positive_integer_validation(self):
        self.assertEqual(self.credential.standby_no_traffic_days, 7)
        for value in (0, -1, 3651, 1.5):
            serializer = ApplicationCredentialSerializer(self.credential, data={'standby_no_traffic_days': value}, partial=True)
            self.assertFalse(serializer.is_valid(), value)
        serializer = ApplicationCredentialSerializer(self.credential, data={'standby_no_traffic_days': 14}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.save().standby_no_traffic_days, 14)

    def test_cannot_start_without_admin_preparation_and_alignment(self):
        with self.assertRaises(JMSException):
            self.manager.start()
        self.manager.prepare(self.admin.name, self.admin.id)
        with self.assertRaises(JMSException):
            self.manager.start()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.active_account_id, self.primary.id)
        self.assertEqual(self.credential.status, 'preparing')

    def test_legacy_api_aligns_and_each_standby_secret_fetch_resets_window(self):
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            self.prepare_legacy()
        self.assertEqual(self.credential.revision, 2)
        info = preparation.info(self.credential)
        self.assertEqual(info['applications'][0]['type'], 'api')
        self.assertEqual(info['eligible_at'], (self.started + timedelta(days=7)).isoformat())
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started + timedelta(days=6)):
            self.assertEqual(self.legacy_fetch(self.backup).status_code, 200)
        self.credential.refresh_from_db()
        self.backup.refresh_from_db()
        self.assertEqual(self.backup.date_last_secret_access, self.started + timedelta(days=6))
        self.assertEqual(preparation.info(self.credential)['eligible_at'], (self.started + timedelta(days=13)).isoformat())
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started + timedelta(days=12)):
            preparation.check(self.credential.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_standby')

    def test_ready_notifies_once_and_does_not_switch_automatically(self):
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            self.prepare_legacy()
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started + timedelta(days=7)), \
                patch('accounts.notifications.CredentialPreparationReadyMsg.publish') as notify:
            preparation.notify_ready(self.credential.id)
            preparation.notify_ready(self.credential.id)
            self.assertEqual(notify.call_count, 1)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'ready_to_switch')
        self.assertEqual(self.credential.active_account_id, self.primary.id)
        self.assertIsNone(self.credential.change_execution_id)

    def test_timeline_exposes_current_observation_and_freezes_the_emitted_waiting_event(self):
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            self.prepare_legacy()
        detail = cycle_detail(self.credential, self.rotation_id)
        observation = detail['preparation']
        self.assertTrue(observation['is_current'])
        self.assertEqual(observation['status'], 'waiting_standby')
        self.assertEqual(observation['standby_account']['id'], str(self.backup.id))
        self.assertEqual(observation['standby_no_traffic_days'], 7)
        self.assertEqual(observation['standby_idle_since'], self.started.isoformat())
        self.assertEqual(observation['eligible_at'], (self.started + timedelta(days=7)).isoformat())
        waiting = next(event for event in detail['events'] if event['event'] == 'rotation.standby.waiting')
        self.assertEqual(waiting['preparation']['eligible_at'], observation['eligible_at'])

        accessed_at = self.started + timedelta(days=2)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=accessed_at):
            self.legacy_fetch(self.backup)
            self.credential.refresh_from_db()
            updated = cycle_detail(self.credential, self.rotation_id)
        self.assertEqual(updated['preparation']['standby_last_access'], accessed_at.isoformat())
        self.assertEqual(updated['preparation']['eligible_at'], (accessed_at + timedelta(days=7)).isoformat())
        self.assertEqual(updated['preparation']['remaining_seconds'], 7 * 86400)
        emitted = next(event for event in updated['events'] if event['id'] == waiting['id'])
        self.assertEqual(emitted['preparation']['eligible_at'], observation['eligible_at'])

    def test_historical_observation_keeps_its_duration_and_access_time_after_another_cycle(self):
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            self.prepare_legacy()
        first = self.rotation_id
        self.manager.cancel()
        self.credential.refresh_from_db()
        serializer = ApplicationCredentialSerializer(
            self.credential, data={'standby_no_traffic_days': 14}, partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.manager.prepare(self.admin.name, self.admin.id)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started + timedelta(days=3)):
            self.legacy_fetch(self.backup)
        self.credential.refresh_from_db()
        old = cycle_detail(self.credential, first)['preparation']
        self.assertFalse(old['is_current'])
        self.assertEqual(old['status'], 'cancelled')
        self.assertEqual(old['standby_no_traffic_days'], 7)
        self.assertIsNone(old['standby_last_access'])
        self.assertEqual(old['eligible_at'], (self.started + timedelta(days=7)).isoformat())
        self.assertIsNone(old['remaining_seconds'])

    def test_observation_completion_remains_in_the_same_switch_cycle(self):
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            self.prepare_legacy()
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started + timedelta(days=7)):
            preparation.check(self.credential.id)
            self.credential.refresh_from_db()
            ready = cycle_detail(self.credential, self.rotation_id)['preparation']
            self.assertEqual(ready['status'], 'ready_to_switch')
            self.assertEqual(ready['remaining_seconds'], 0)
            self.manager.start(self.admin.name, self.admin.id)
        self.credential.refresh_from_db()
        finished = cycle_detail(self.credential, self.rotation_id)['preparation']
        self.assertFalse(finished['is_current'])
        self.assertEqual(finished['status'], 'completed')
        self.assertEqual(finished['ready_at'], (self.started + timedelta(days=7)).isoformat())

    def test_stale_account_edits_preserve_latest_secret_access(self):
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            self.prepare_legacy()
        metadata_edit = type(self.backup).objects.get(id=self.backup.id)
        secret_edit = type(self.backup).objects.get(id=self.backup.id)
        last_access = self.started + timedelta(days=6)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=last_access):
            self.legacy_fetch(self.backup)
        metadata_edit.comment = 'Edited after an API request'
        metadata_edit.save()
        secret_edit.secret = 'new-backup-secret'
        secret_edit.save()
        self.backup.refresh_from_db()
        self.assertEqual(self.backup.date_last_secret_access, last_access)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started + timedelta(days=7)):
            preparation.check(self.credential.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_standby')
        self.assertEqual(preparation.info(self.credential)['eligible_at'], (last_access + timedelta(days=7)).isoformat())

    def test_standby_access_revokes_ready_and_blocks_start(self):
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            self.prepare_legacy()
        later = self.started + timedelta(days=7)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=later):
            preparation.check(self.credential.id)
            self.legacy_fetch(self.backup)
            with self.assertRaises(JMSException):
                self.manager.start()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_standby')

    def test_switch_keeps_preparation_cycle_and_waits_for_legacy_target_access(self):
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            self.prepare_legacy()
        later = self.started + timedelta(days=7)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=later):
            preparation.check(self.credential.id)
            self.manager.start(self.admin.name, self.admin.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_switch')
        self.assertEqual(self.credential.active_account_id, self.backup.id)
        self.assertEqual(self.credential.rotation_records.count(), 1)
        self.assertEqual(self.credential.rotation_records.first().id, self.rotation_id)
        _, blockers = self.manager.check_usage()
        self.assertEqual(len(blockers), 1)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=later + timedelta(seconds=1)):
            self.legacy_fetch(self.backup)
        _, blockers = self.manager.check_usage()
        self.assertEqual(blockers, [])
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'ready_for_change')
        detail = cycle_detail(self.credential, self.rotation_id)
        self.assertIn('rotation.preparation.ready', [event['event'] for event in detail['events']])
        self.assertIn('rotation.started', [event['event'] for event in detail['events']])

    def test_sdk_alignment_requires_apply_confirmation_and_every_fetch_counts(self):
        configuration = ClientAccessConfiguration.objects.create(application=self.application, name='Prep SDK', type='sdk')
        configuration.credentials.add(self.credential)
        client = CredentialClientManager(self.application, configuration.id, 'prep-sdk')
        self.manager.prepare(self.admin.name, self.admin.id)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            client.fetch(self.credential.key, '127.0.0.1')
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'preparing')
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started + timedelta(seconds=1)):
            client.confirm(self.credential.key, self.credential.revision, self.primary.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_standby')
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started + timedelta(seconds=2)):
            client.fetch(self.credential.key, '127.0.0.1')
        self.primary.refresh_from_db()
        self.assertEqual(self.primary.date_last_secret_access, self.started + timedelta(seconds=2))

    def test_failed_sdk_secret_read_is_not_traffic(self):
        from accounts.exceptions import VaultSecretNotFoundException
        configuration = ClientAccessConfiguration.objects.create(application=self.application, name='Prep SDK', type='sdk')
        configuration.credentials.add(self.credential)
        client = CredentialClientManager(self.application, configuration.id, 'prep-sdk')
        self.manager.prepare(self.admin.name, self.admin.id)
        with patch.object(Account, 'secret', new_callable=PropertyMock, side_effect=VaultSecretNotFoundException):
            with self.assertRaises(VaultSecretNotFoundException):
                client.fetch(self.credential.key, '127.0.0.1')
        self.primary.refresh_from_db()
        self.assertIsNone(self.primary.date_last_secret_access)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'preparing')

    def test_an_application_without_alignment_blocks_preparation(self):
        other = IntegrationApplication.objects.create(name='Other app', accounts={'type': 'ids', 'ids': [str(self.primary.id), str(self.backup.id)]})
        CredentialApplicationBinding.objects.create(credential=self.credential, application=other)
        self.manager.prepare(self.admin.name, self.admin.id)
        self.legacy_fetch(self.primary)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started + timedelta(days=30)):
            preparation.check(self.credential.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'preparing')

    @override_settings(SECURITY_DISABLE_VIEW_SECRET=True)
    def test_legacy_secret_hidden_by_setting_is_not_traffic_or_alignment(self):
        self.manager.prepare(self.admin.name, self.admin.id)
        response = self.legacy_fetch(self.primary)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['secret'])
        self.primary.refresh_from_db()
        self.assertIsNone(self.primary.date_last_secret_access)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'preparing')

    def test_preparation_can_be_cancelled_without_switching_or_secret_change(self):
        self.manager.prepare(self.admin.name, self.admin.id)
        self.manager.cancel()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'idle')
        self.assertEqual(self.credential.active_account_id, self.primary.id)
        self.assertEqual(self.primary.secret, 'primary-secret')
        rotation = self.credential.rotation_records.first()
        self.assertEqual(rotation.status, 'cancelled')
        self.assertIsNone(rotation.change_execution_id)

    def test_window_cannot_be_changed_during_preparation(self):
        self.manager.prepare(self.admin.name, self.admin.id)
        self.credential.refresh_from_db()
        serializer = ApplicationCredentialSerializer(self.credential, data={'standby_no_traffic_days': 1}, partial=True)
        self.assertFalse(serializer.is_valid())

    def test_mixed_legacy_and_sdk_requests_are_checked_after_switching(self):
        configuration = ClientAccessConfiguration.objects.create(application=self.application, name='Mixed SDK', type='sdk')
        configuration.credentials.add(self.credential)
        client = CredentialClientManager(self.application, configuration.id, 'mixed-sdk')
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            self.manager.prepare(self.admin.name, self.admin.id)
            self.legacy_fetch(self.primary)
            fetched = client.fetch(self.credential.key, '127.0.0.1')
            client.confirm(self.credential.key, fetched['revision'], self.primary.id)
        later = self.started + timedelta(days=7)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=later):
            preparation.check(self.credential.id)
            self.manager.start()
            fetched = client.fetch(self.credential.key, '127.0.0.1')
            client.confirm(self.credential.key, fetched['revision'], self.backup.id)
            CredentialClientInstance.objects.filter(id=client.client.id).update(date_last_seen=later)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=later + timedelta(seconds=1)):
            self.legacy_fetch(self.primary)
            _, blockers = self.manager.check_usage()
            self.assertTrue(blockers)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=later + timedelta(seconds=2)):
            client.fetch(self.credential.key, '127.0.0.1')
            _, blockers = self.manager.check_usage()
            self.assertFalse(blockers)

    def test_standby_traffic_during_preflight_prevents_publication(self):
        from accounts.credential_rotation import preflight
        self.precheck_patch.stop()
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=self.started):
            self.prepare_legacy()
        later = self.started + timedelta(days=7)
        with patch('accounts.credential_rotation.preparation.timezone.now', return_value=later), \
                patch('accounts.credential_rotation.preflight.dispatch'):
            preparation.check(self.credential.id)
            self.manager.start(self.admin.name, self.admin.id)
            execution = preflight.latest(self.credential)
            execution.status = 'success'
            execution.summary = {'ok_assets': 1, 'fail_assets': 0, 'error_assets': 0}
            execution.date_finished = later
            execution.save()
            self.legacy_fetch(self.backup)
            preflight.finish(execution.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.active_account_id, self.primary.id)
        self.assertEqual(self.credential.status, 'waiting_standby')
        self.assertEqual(self.credential.rotation_records.first().status, 'preparing')
