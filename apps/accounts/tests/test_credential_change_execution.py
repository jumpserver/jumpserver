from unittest.mock import patch

from django.utils import timezone
from django.db import transaction
from django.utils import translation
from rest_framework.exceptions import ValidationError

from accounts.api.automations.change_secret import (
    ChangeSecretAutomationViewSet, ChangSecretExecutionViewSet,
)
from accounts.credential_rotation import CredentialRotationManager
from accounts.credential_rotation.execution import execute, reconcile, outcome
from accounts.models import AutomationExecution, ChangeSecretRecord
from accounts.tasks.common import execute_credential_change
from accounts.tests.base import CredentialTestCase
from common.exceptions import JMSException


class CredentialChangeExecutionTests(CredentialTestCase):
    def setUp(self):
        language = translation.get_language()
        self.addCleanup(translation.activate, language)
        super().setUp()
        self.credential.rotation_mode = 'single'
        self.credential.backup_account = None
        self.credential.save()
        self.manager = CredentialRotationManager(self.credential.id)
        self.manager.start()
        self.rotation = self.credential.rotation_records.get()

    def save_task(self, **overrides):
        data = {
            'name': 'PAM execution test', 'rotation_id': str(self.rotation.id),
            'accounts': [self.primary.username], 'assets': [str(self.asset.id)],
            'nodes': [], 'secret_type': self.primary.secret_type,
            'secret_strategy': 'specific', 'secret': 'candidate-secret',
            'is_periodic': False, 'check_conn_after_change': True,
        }
        data.update(overrides)
        view = ChangeSecretAutomationViewSet.as_view({'post': 'create'})
        with transaction.atomic():
            return view(self.request('post', '/api/v1/accounts/change-secret-automations/', data))

    def start_execution(self):
        response = self.save_task()
        self.assertEqual(response.status_code, 201, response.data)
        self.rotation.refresh_from_db()
        return execute(self.rotation.id, self.admin.name)

    def test_save_binds_on_pam_record_without_starting_change(self):
        response = self.save_task()
        self.assertEqual(response.status_code, 201, response.data)
        self.rotation.refresh_from_db()
        self.credential.refresh_from_db()
        self.assertEqual(str(self.rotation.change_automation_id), str(response.data['id']))
        self.assertEqual(self.credential.status, 'ready_for_change')
        self.assertIsNone(self.credential.change_execution_id)
        self.assertEqual(self.save_task(name='duplicate').status_code, 400)

    def test_task_cannot_target_other_account_or_be_periodic(self):
        for changes in (
            {'accounts': [self.backup.username]}, {'is_periodic': True},
            {'check_conn_after_change': False}, {'assets': []},
        ):
            with self.subTest(changes=changes):
                response = self.save_task(**changes)
                self.assertEqual(response.status_code, 400)
                self.assertIsInstance(response.data['detail'], str)
                self.assertTrue(response.data['detail'])
                self.assertIn('code', response.data)
        self.assertIsNone(self.rotation.change_automation_id)

    def test_rotation_form_field_errors_return_detail(self):
        for changes in (
            {'name': ''}, {'rotation_id': 'invalid-uuid'},
            {'password_rules': {'length': 'invalid-length'}},
        ):
            with self.subTest(changes=changes):
                response = self.save_task(**changes)
                self.assertEqual(response.status_code, 400)
                self.assertIsInstance(response.data['detail'], str)
                self.assertTrue(response.data['detail'])
                self.assertEqual(response.data['code'], 'invalid')

    def test_normal_task_keeps_existing_field_error_contract(self):
        response = self.save_task(rotation_id=None, name='')
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.data)
        self.assertNotIn('detail', response.data)

    def test_task_list_execution_binds_once_and_dispatches_after_commit(self):
        self.assertEqual(self.save_task().status_code, 201)
        self.rotation.refresh_from_db()
        view = ChangSecretExecutionViewSet.as_view({'post': 'create'})
        with patch('accounts.credential_rotation.execution.dispatch') as dispatch:
            with self.captureOnCommitCallbacks(execute=True):
                data = {'automation': str(self.rotation.change_automation_id)}
                first = view(self.request('post', '/api/v1/accounts/change-secret-executions/', data))
                second = view(self.request('post', '/api/v1/accounts/change-secret-executions/', data))
                self.assertEqual(first.status_code, 201, first.data)
                self.assertEqual(first.data['task'], second.data['task'])
                dispatch.assert_not_called()
            self.assertTrue(dispatch.called)
        self.assertEqual(AutomationExecution.objects.count(), 1)
        self.credential.refresh_from_db()
        self.assertEqual(str(self.credential.change_execution_id), first.data['task'])
        self.assertEqual(self.credential.status, 'changing_secret')

    def test_blocked_rotation_returns_displayable_detail_without_dispatch(self):
        from accounts.api.account.credential import ApplicationCredentialViewSet
        from accounts.models import ApplicationCredential

        self.assertEqual(self.save_task().status_code, 201)
        self.rotation.refresh_from_db()
        self.credential.refresh_from_db()
        self.credential.rotation_mode = 'dual'
        self.credential.backup_account = self.backup
        self.credential.save()
        expected = {
            'detail': 'Wait for all enabled clients to apply the backup account.',
            'code': 'credential_rotation_clients_not_ready',
        }
        with translation.override('en'), patch.object(
            ApplicationCredential, 'get_blockers', return_value=[{'online': False}],
        ), patch('accounts.credential_rotation.execution.dispatch') as dispatch:
            view = ChangSecretExecutionViewSet.as_view({'post': 'create'})
            with transaction.atomic():
                response = view(self.request('post', '/api/v1/accounts/change-secret-executions/', {
                    'automation': str(self.rotation.change_automation_id),
                }))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, expected)
            view = ApplicationCredentialViewSet.as_view({'post': 'change_secret'})
            with transaction.atomic():
                response = view(self.request('post', '/'), pk=self.credential.id)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, expected)
            dispatch.assert_not_called()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'ready_for_change')
        self.assertFalse(AutomationExecution.objects.exists())

    def test_finished_rotation_task_is_not_a_normal_task(self):
        self.assertEqual(self.save_task().status_code, 201)
        self.rotation.refresh_from_db()
        self.manager.cancel()
        self.manager.complete()
        with self.assertRaises(JMSException):
            execute(self.rotation.id)

    def test_unrelated_success_never_publishes(self):
        bound = self.start_execution()
        other = AutomationExecution.objects.create(type='change_secret', status='success')
        ChangeSecretRecord.objects.create(
            execution=other, account=self.primary, asset=self.asset,
            account_version=self.primary.version, new_secret=self.primary.secret,
            status='success', date_finished=timezone.now(),
        )
        self.assertEqual(self.manager.check_secret_change().status, 'changing_secret')
        self.assertEqual(outcome(self.credential, bound), 'running')

    def test_duplicate_worker_delivery_claims_only_once(self):
        execution = self.start_execution()

        def finish(instance):
            instance.status = 'failed'
            instance.date_finished = timezone.now()
            instance.save(update_fields=['status', 'date_finished'])

        with patch.object(AutomationExecution, 'start', autospec=True, side_effect=finish) as start:
            execute_credential_change(str(execution.id), self.org.id)
            execute_credential_change(str(execution.id), self.org.id)
        self.assertEqual(start.call_count, 1)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'change_failed')
        self.assertEqual(self.manager.cancel(reason='No remote change').status, 'waiting_primary')

    def test_unverified_requires_recovery_and_verified_sync_allows_publish(self):
        execution = self.start_execution()
        execution.status = 'failed'
        execution.date_finished = timezone.now()
        execution.save()
        record = ChangeSecretRecord.objects.create(
            account=self.primary, asset=self.asset, execution=execution,
            old_secret=self.primary.secret, new_secret='new-secret',
            account_version=self.primary.version, status='unverified',
            date_finished=timezone.now(),
        )
        reconcile(execution.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'recovery_required')
        with self.assertRaises(JMSException):
            self.manager.cancel(reason='Unsafe')
        record.verification_status = 'success'
        record.save()
        self.assertEqual(self.manager.check_secret_change().status, 'recovery_required')
        self.primary.secret = record.new_secret
        self.primary.save()
        self.assertEqual(self.manager.check_secret_change().status, 'waiting_primary')
        revision = self.manager.check_secret_change().revision
        self.assertEqual(self.manager.check_secret_change().revision, revision)

    def test_retry_and_old_callback_do_not_overwrite_current_attempt(self):
        execution = self.start_execution()
        execution.status = 'failed'
        execution.date_finished = timezone.now()
        execution.summary = {'rotation_no_remote_change': True}
        execution.save()
        reconcile(execution.id)
        retry = execute(self.rotation.id, previous_execution_id=execution.id, reason='Fixed parameters')
        duplicate = execute(self.rotation.id, previous_execution_id=execution.id, reason='Fixed parameters')
        self.assertEqual(retry.id, duplicate.id)
        reconcile(execution.id)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.change_execution_id, retry.id)
        self.assertEqual(self.credential.status, 'changing_secret')

    def test_interrupted_rotation_notifies_in_execution_organization(self):
        from accounts.automations.recovery import finalize_interrupted_execution
        from accounts.models import ClientAccessConfiguration, CredentialClientInstance, ApplicationEventDelivery
        from orgs.utils import tmp_to_root_org

        configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Recovery listener', type='sdk', notification_enabled=True,
        )
        configuration.credentials.add(self.credential)
        client = CredentialClientInstance.objects.create(
            application=self.application, configuration=configuration, type='sdk',
            instance_id='recovery-listener', events_enabled=True,
        )
        execution = self.start_execution()
        ChangeSecretRecord.objects.create(
            execution=execution, account=self.primary, asset=self.asset,
            old_secret=self.primary.secret, new_secret='candidate',
            account_version=self.primary.version, status='pending',
        )
        with tmp_to_root_org():
            self.assertTrue(finalize_interrupted_execution(execution.id, 'Worker interrupted'))
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'recovery_required')
        delivery = ApplicationEventDelivery.objects.filter(
            client=client, code='rotation.failed',
        ).first()
        self.assertIsNotNone(delivery)
        self.assertEqual(str(delivery.org_id), str(self.org.id))

    def test_legacy_unbound_change_requires_verification(self):
        self.credential.status = 'changing_secret'
        self.credential.save()
        self.assertEqual(self.manager.check_secret_change().status, 'recovery_required')

    def test_active_task_and_execution_cannot_be_deleted(self):
        execution = self.start_execution()
        with self.assertRaises(ValidationError), transaction.atomic():
            execution.delete()
        with self.assertRaises(ValidationError), transaction.atomic():
            self.rotation.change_automation.delete()
        self.assertTrue(AutomationExecution.objects.filter(id=execution.id).exists())

    def test_broker_failure_preserves_pending_execution_for_redispatch(self):
        from accounts.credential_rotation.execution import dispatch
        execution = self.start_execution()
        with patch('accounts.tasks.common.execute_credential_change.apply_async', side_effect=OSError('broker unavailable')):
            dispatch(execution.id, self.org.id)
        execution.refresh_from_db()
        self.assertEqual(execution.status, 'pending')
        self.assertEqual(execute(self.rotation.id).id, execution.id)

    def test_normal_change_cannot_bypass_active_rotation(self):
        from accounts.automations.base.manager import BaseChangeSecretPushManager
        manager = object.__new__(BaseChangeSecretPushManager)
        manager.execution = AutomationExecution.objects.create(type='change_secret')
        manager.account_locks = {}
        with self.assertRaises(ValueError):
            manager.acquire_account_lock(self.primary.id)
        bound = self.start_execution()
        manager.execution = bound
        try:
            self.assertTrue(manager.acquire_account_lock(self.primary.id))
        finally:
            manager.release_all_account_locks()

    def test_task_creation_requires_pam_permission(self):
        from users.models import User
        original = User.has_perm

        def permission(user, perm, *args, **kwargs):
            if perm == 'accounts.change_applicationcredential':
                return False
            return original(user, perm, *args, **kwargs)

        with patch.object(User, 'has_perm', permission):
            self.assertEqual(self.save_task().status_code, 403)
        self.rotation.refresh_from_db()
        self.assertIsNone(self.rotation.change_automation_id)

    def test_force_restore_cannot_turn_unverified_rotation_into_success(self):
        from accounts.api.automations.change_secret import ChangeSecretRecordViewSet
        from rest_framework.permissions import AllowAny
        execution = self.start_execution()
        record = ChangeSecretRecord.objects.create(
            execution=execution, account=self.primary, asset=self.asset,
            old_secret=self.primary.secret, new_secret='unverified-candidate',
            account_version=self.primary.version, status='unverified',
        )
        view = ChangeSecretRecordViewSet.as_view({'post': 'restore'})
        with patch.object(ChangeSecretRecordViewSet, 'get_permissions', return_value=[AllowAny()]):
            response = view(self.request('post', '/api/v1/accounts/change-secret-records/restore/', {
                'record_ids': [str(record.id)], 'force': True,
            }))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['not_verified'], 1)
        record.refresh_from_db()
        self.assertEqual(record.status, 'unverified')
