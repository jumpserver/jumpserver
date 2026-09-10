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
        self.assertEqual(self.credential.published_account_id, self.primary.id)
        self.assertEqual(self.credential.revision, 1)
        self.assertFalse(self.credential.rotation_records.exists())
        self.assertEqual(preflight.info(ApplicationCredential.objects.get(pk=self.credential.pk))['status'], 'checking')

    def test_success_publishes_once_and_runs_existing_verifier(self):
        execution = self.start()
        with patch.object(AutomationExecution, 'start', autospec=True, side_effect=self.verified) as verify:
            preflight.run(execution.id)
            preflight.run(execution.id)
            preflight.finish(execution.id)
        self.assertEqual(verify.call_count, 1)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_backup')
        self.assertEqual(self.credential.published_account_id, self.backup.id)
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
        conflict = ApplicationCredential.objects.create(
            name='Conflicting fixed credential', type='fixed', rotation_mode='',
            primary_account=self.backup, published_account=self.backup,
        )
        with self.assertRaisesMessage(JMSException, conflict.name):
            self.start()
        self.assertFalse(AutomationExecution.objects.exists())

    def test_serializer_rejects_cross_primary_backup_ownership(self):
        other = Account.objects.create(name='other', username='other', secret='secret', asset=self.asset)
        for account in (self.primary, self.backup):
            serializer = ApplicationCredentialSerializer(data={
                'name': 'Conflicting', 'type': 'rotation', 'rotation_mode': 'dual',
                'primary_account': str(other.id), 'backup_account': str(account.id),
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
        self.assertEqual(self.credential.published_account_id, self.primary.id)
        self.assertEqual(self.credential.revision, 1)

    def test_dual_start_requires_account_verification_permission(self):
        from users.models import User
        original = User.has_perm
        with patch.object(User, 'has_perm', lambda user, perm, *args, **kwargs:
                          perm != 'accounts.verify_account' and original(user, perm, *args, **kwargs)):
            view = ApplicationCredentialViewSet.as_view({'post': 'start_rotation'})
            with transaction.atomic():
                response = view(self.request('post', '/'), pk=self.credential.id)
            self.assertEqual(response.status_code, 403)
        self.assertFalse(AutomationExecution.objects.exists())
