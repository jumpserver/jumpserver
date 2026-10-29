from datetime import timedelta
from unittest.mock import patch

from django.db import transaction
from django.utils import timezone

from accounts.api.account.credential import ApplicationCredentialViewSet
from accounts.credential_rotation import CredentialRotationManager
from accounts.credential_rotation import preflight
from accounts.models import Account, ApplicationCredential, AutomationExecution, ApplicationAudit
from accounts.serializers import ApplicationCredentialSerializer
from accounts.tests.base import CredentialTestCase
from common.exceptions import JMSException


class CredentialPreflightTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.precheck_patch.stop()
        self.manager = CredentialRotationManager(self.credential.id)

    def start(self):
        self.manager.start(self.admin.name, self.admin.id)
        return preflight.latest(self.credential)

    @staticmethod
    def verified(execution):
        execution.status = 'success'
        execution.summary = {'ok_assets': 1, 'fail_assets': 0, 'error_assets': 0}
        execution.date_finished = timezone.now()
        execution.save()

    def test_api_start_queues_once_without_publishing(self):
        self.assertTrue(self.credential.verify_before_switch)
        view = ApplicationCredentialViewSet.as_view({'post': 'start_rotation'})
        with patch('accounts.credential_rotation.preflight.dispatch') as dispatch:
            with self.captureOnCommitCallbacks(execute=True):
                first = view(self.request('post', '/'), pk=self.credential.id)
                second = view(self.request('post', '/'), pk=self.credential.id)
                self.assertEqual(first.status_code, 200, first.data)
                self.assertEqual(first.data['precheck']['status'], 'checking')
                self.assertEqual(first.data['precheck']['execution_id'], second.data['precheck']['execution_id'])
                dispatch.assert_not_called()
            self.assertEqual(dispatch.call_count, 1)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.active_account_id, self.primary.id)
        self.assertEqual(self.credential.revision, 1)
        rotation = self.credential.rotation_records.get()
        self.assertEqual(rotation.status, 'preparing')
        self.assertEqual(rotation.source_account_id, self.primary.id)
        self.assertEqual(rotation.events.first().event, 'rotation.verify.started')
        self.assertEqual(preflight.info(ApplicationCredential.objects.get(pk=self.credential.pk))['status'], 'checking')

    def test_success_publishes_once_and_runs_existing_verifier(self):
        execution = self.start()
        with patch.object(AutomationExecution, 'start', autospec=True, side_effect=self.verified) as verify:
            preflight.run(execution.id)
            preflight.run(execution.id)
            preflight.finish(execution.id)
        self.assertEqual(verify.call_count, 1)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_switch')
        self.assertEqual(self.credential.active_account_id, self.backup.id)
        self.assertEqual(self.credential.revision, 2)
        self.assertEqual(self.credential.rotation_records.count(), 1)

    def test_failures_and_timeouts_never_publish(self):
        execution = self.start()
        execution.status = 'failed'
        execution.date_finished = timezone.now()
        execution.save()
        preflight.finish(execution.id)
        self.assertEqual(preflight.info(self.credential)['status'], 'failed')
        retry = self.start()
        with patch('accounts.credential_rotation.preflight.timezone.now', return_value=timezone.now() + timedelta(minutes=11)):
            self.assertEqual(preflight.info(self.credential)['code'], 'timeout')
            self.verified(retry)
            preflight.finish(retry.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.revision, 1)
        self.assertEqual(self.credential.status, 'idle')

    def test_changed_password_and_stale_callback_rejected(self):
        execution = self.start()
        self.backup.secret = 'changed-during-verification'
        self.backup.save()
        self.verified(execution)
        preflight.finish(execution.id)
        self.assertEqual(preflight.info(self.credential)['code'], 'changed')
        retry = self.start()
        self.verified(execution)
        preflight.finish(execution.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'idle')
        self.assertEqual(preflight.latest(self.credential).id, retry.id)

    def test_rejected_dispatch_cannot_be_overwritten_by_late_runner(self):
        execution = self.start()
        preflight.fail(execution.id, 'dispatch_failed')
        execution.refresh_from_db()
        self.verified(execution)
        preflight.finish(execution.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'idle')
        self.assertEqual(preflight.info(self.credential)['code'], 'dispatch_failed')

    def test_invalid_account_and_cross_ownership_rejected(self):
        self.backup.is_active = False
        self.backup.save()
        with self.assertRaises(JMSException):
            self.start()
        self.backup.is_active = True
        self.backup.save()
        other = Account.objects.create(
            name='conflict-other', username='conflict-other',
            asset=self.asset, secret='secret',
        )
        conflict = ApplicationCredential.objects.create(
            name='Conflicting credential',
            mode=ApplicationCredential.Mode.alternating_rotation,
            account=self.backup, alternate_account=other,
            active_account=self.backup,
        )
        with self.assertRaisesMessage(JMSException, conflict.name):
            self.start()
        self.assertFalse(AutomationExecution.objects.exists())

    def test_disabled_verification_publishes_without_probe_and_records_skip(self):
        self.credential.verify_before_switch = False
        self.credential.save(update_fields=['verify_before_switch'])
        with patch('accounts.credential_rotation.preflight.dispatch') as dispatch:
            self.start()
        dispatch.assert_not_called()
        self.assertFalse(AutomationExecution.objects.exists())
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.active_account_id, self.backup.id)
        self.assertEqual(self.credential.status, 'waiting_switch')
        self.assertEqual(self.credential.revision, 2)
        rotation = self.credential.rotation_records.get()
        self.assertEqual(rotation.status, 'running')
        events = list(rotation.events.order_by('sequence').values_list('event', flat=True))
        self.assertEqual(events[0], 'rotation.verify.skipped')
        self.assertIn('rotation.started', events)
        self.assertNotIn('rotation.verify.started', events)
        self.assertIsNone(preflight.info(self.credential))
        self.primary.refresh_from_db()
        self.backup.refresh_from_db()
        self.assertEqual(self.primary.secret, 'primary-secret')
        self.assertEqual(self.backup.secret, 'backup-secret')

    def test_skip_keeps_source_observation_and_post_change_verification(self):
        from accounts.credential_rotation.execution import validate_parameters
        self.credential.verify_before_switch = False
        self.credential.source_no_traffic_days = 7
        self.credential.save(update_fields=['verify_before_switch', 'source_no_traffic_days'])
        self.start()
        credential, blockers = self.manager.check_usage()
        self.assertEqual(credential.status, 'waiting_switch')
        self.assertTrue(blockers)
        self.assertFalse(AutomationExecution.objects.exists())
        with self.assertRaises(JMSException):
            validate_parameters(credential, {
                'assets': [self.asset], 'accounts': [self.primary.username],
                'secret_type': self.primary.secret_type, 'check_conn_after_change': False,
            })

    def test_skip_still_waits_for_application_confirmation(self):
        from accounts.models import CredentialClientInstance
        client = CredentialClientInstance.objects.create(
            application=self.application, instance_id='skip-verification-app', type='sdk',
        )
        self.credential.verify_before_switch = False
        self.credential.save(update_fields=['verify_before_switch'])
        self.start()
        credential, blockers = self.manager.check_usage()
        self.assertEqual(credential.status, 'waiting_switch')
        self.assertTrue(blockers)
        state = client.credential_statuses.get()
        self.assertTrue(state.is_rotation_participant)
        self.assertEqual(state.required_revision, credential.revision)
        self.assertNotEqual(state.applied_revision, credential.revision)
        with self.assertRaises(JMSException):
            self.manager.change_secret()

    def test_skip_still_requires_usable_account_configuration(self):
        self.credential.verify_before_switch = False
        self.credential.save(update_fields=['verify_before_switch'])
        self.backup.is_active = False
        self.backup.save(update_fields=['is_active'])
        with self.assertRaises(JMSException):
            self.start()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.active_account_id, self.primary.id)
        self.assertFalse(self.credential.rotation_records.exists())

    def test_policy_api_persists_verification_switch(self):
        view = ApplicationCredentialViewSet.as_view({'patch': 'partial_update'})
        response = view(self.request('patch', '/', {'verify_before_switch': False}), pk=self.credential.id)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data['verify_before_switch'])
        self.credential.refresh_from_db()
        self.assertFalse(self.credential.verify_before_switch)

    def test_verification_switch_cannot_change_during_probe_or_rotation(self):
        execution = self.start()
        serializer = ApplicationCredentialSerializer(
            self.credential, data={'verify_before_switch': False}, partial=True,
        )
        self.assertFalse(serializer.is_valid())
        preflight.fail(execution.id, 'failed')
        serializer = ApplicationCredentialSerializer(
            self.credential, data={'verify_before_switch': False}, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.start()
        self.credential.refresh_from_db()
        serializer = ApplicationCredentialSerializer(
            self.credential, data={'verify_before_switch': True}, partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIsNone(preflight.info(self.credential))

    def test_queued_probe_rejects_out_of_band_verification_switch_change(self):
        execution = self.start()
        ApplicationCredential.objects.filter(pk=self.credential.pk).update(verify_before_switch=False)
        with patch.object(AutomationExecution, 'start') as probe:
            preflight.run(execution.id)
        probe.assert_not_called()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.active_account_id, self.primary.id)
        self.assertEqual(self.credential.revision, 1)

    def test_skip_routes_do_not_require_account_verification_permission(self):
        from users.models import User
        self.credential.verify_before_switch = False
        self.credential.save(update_fields=['verify_before_switch'])
        original = User.has_perm
        with patch.object(User, 'has_perm', lambda user, perm, *args, **kwargs:
                          perm != 'accounts.verify_account' and original(user, perm, *args, **kwargs)):
            for action in ('start_rotation', 'start_cycle', 'prepare_rotation'):
                with self.subTest(action=action), transaction.atomic():
                    view = ApplicationCredentialViewSet.as_view({'post': action})
                    response = view(self.request('post', '/'), pk=self.credential.id)
                    self.assertIn(response.status_code, (200, 201), response.data)
                    transaction.set_rollback(True)
        self.assertFalse(AutomationExecution.objects.exists())

    def test_account_must_allow_secret_reset(self):
        self.primary.secret_reset = False
        self.primary.save(update_fields=['secret_reset'])
        with self.assertRaises(JMSException) as error:
            self.start()
        self.assertEqual(error.exception.detail.code, 'credential_account_secret_reset_disabled')
        self.assertFalse(AutomationExecution.objects.exists())

    def test_serializer_rejects_cross_primary_backup_ownership(self):
        other = Account.objects.create(name='other', username='other', secret='secret', asset=self.asset)
        for account in (self.primary, self.backup):
            serializer = ApplicationCredentialSerializer(data={
                'name': 'Conflicting', 'mode': ApplicationCredential.Mode.alternating_rotation,
                'account': str(other.id), 'alternate_account': str(account.id),
                'applications': [str(self.application.id)],
            })
            with self.subTest(account=account.id), self.assertRaises(JMSException):
                serializer.is_valid(raise_exception=True)

    def test_empty_success_cannot_reuse_old_account_connectivity(self):
        execution = self.start()
        self.backup.set_connectivity('ok')
        self.verified(execution)
        execution.summary = {'ok_assets': 0}
        execution.save()
        preflight.finish(execution.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.revision, 1)
        self.assertFalse(ApplicationAudit.objects.filter(
            credential_id=self.credential.id, event='rotation_started',
        ).exists())

    def test_permission_revocation_and_configuration_edit_prevent_probe(self):
        execution = self.start()
        with patch('accounts.credential_rotation.preflight.authorized', return_value=False), patch.object(
            AutomationExecution, 'start',
        ) as probe:
            preflight.run(execution.id)
            probe.assert_not_called()
        retry = self.start()
        self.credential.comment = 'edited while queued'
        self.credential.save()
        with patch.object(AutomationExecution, 'start') as probe:
            preflight.run(retry.id)
            probe.assert_not_called()
        self.assertEqual(preflight.info(self.credential)['code'], 'changed')

    def test_account_busy_at_publication_keeps_primary(self):
        execution = self.start()
        self.verified(execution)
        with patch('accounts.credential_rotation.preflight.cache.lock') as lock:
            lock.return_value.acquire.return_value = False
            preflight.finish(execution.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'idle')
        self.assertEqual(self.credential.active_account_id, self.primary.id)
        self.assertEqual(self.credential.revision, 1)

    def test_dual_start_requires_account_verification_permission(self):
        from users.models import User
        original = User.has_perm
        with patch.object(User, 'has_perm', lambda user, perm, *args, **kwargs:
                          perm != 'accounts.verify_account' and original(user, perm, *args, **kwargs)):
            for action in ('start_rotation', 'start_cycle', 'prepare_rotation'):
                view = ApplicationCredentialViewSet.as_view({'post': action})
                with transaction.atomic():
                    response = view(self.request('post', '/'), pk=self.credential.id)
                self.assertEqual(response.status_code, 403, action)
        self.assertFalse(AutomationExecution.objects.exists())
