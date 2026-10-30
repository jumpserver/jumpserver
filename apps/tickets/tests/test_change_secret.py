from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.db import transaction
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone

from accounts.const import SecretStrategy, SecretType
from accounts.models import Account, AutomationExecution, ChangeSecretRecord
from assets.models import PlatformAutomation
from orgs.utils import tmp_to_org
from rbac.models import Permission, Role, RoleBinding
from tickets.plugins import get_ticket_plugin
from tickets.plugins.change_secret.execution import dispatch_execution, execute
from tickets.serializers.ticket.ticket import TicketSerializer
from tickets.tasks import dispatch_ticket_change_secrets
from tickets.tests import test_plugins as helpers
from tickets.workflow.business import submit_ticket
from tickets.workflow.errors import WorkflowConflict


@override_settings(XPACK_LICENSE_IS_VALID=True, TICKET_APPLY_ASSET_SCOPE='all',
                   CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED=False)
class ChangeSecretTests(TestCase):
    setUpTestData = helpers.TicketPluginTests.__dict__['setUpTestData']
    workflow = helpers.TicketPluginTests.workflow
    task = helpers.TicketPluginTests.task
    payload = helpers.TicketPluginTests.payload
    serializer = helpers.TicketPluginTests.serializer

    def setUp(self):
        helpers.TicketPluginTests.setUp(self)
        push = patch('accounts.signal_handlers.push_accounts_if_need.delay')
        push.start()
        self.addCleanup(push.stop)
        PlatformAutomation.objects.update_or_create(platform=self.platform, defaults={
            'ansible_enabled': True, 'change_secret_enabled': True, 'change_secret_method': 'change_secret_posix',
        })
        self.account = Account.objects.create(asset=self.asset, name='service', username='service',
                                              secret='original-private-password')
        self.plugin = get_ticket_plugin('change_secret')

    def request_ticket(self, approved=False, levels=1):
        payload = self.payload('change_secret', asset=str(self.asset.pk), accounts=['service'])
        payload['workflow_id'] = str(self.workflow('change_secret', levels=levels).pk)
        serializer = self.serializer(payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        instance = submit_ticket(ticket)
        if approved:
            self.engine.approve(self.task(instance), self.alice)
        ticket.refresh_from_db()
        instance.refresh_from_db()
        return ticket, instance

    def test_final_approval_persists_one_job_and_dispatches_only_after_commit(self):
        ticket, instance = self.request_ticket(levels=2)
        with patch('tickets.tasks.execute_ticket_change_secret.delay') as delay:
            with self.captureOnCommitCallbacks(execute=True):
                self.engine.approve(self.task(instance), self.alice)
                self.assertFalse(AutomationExecution.objects.filter(pk=ticket.pk).exists())
            delay.assert_not_called()
            final_task = self.task(instance)
            with self.captureOnCommitCallbacks(execute=True):
                self.engine.approve(final_task, self.alice)
                delay.assert_not_called()
            delay.assert_called_once_with(str(ticket.pk))
        job = AutomationExecution.objects.get(pk=ticket.pk)
        self.assertEqual(job.status, 'pending')
        self.assertIsNone(job.date_start)
        self.assertEqual(job.snapshot['accounts'], [str(self.account.pk)])
        self.assertEqual(job.snapshot['assets'], [str(self.asset.pk)])
        self.assertEqual(job.snapshot['secret_strategy'], SecretStrategy.random)
        self.assertTrue(job.snapshot['check_conn_after_change'])
        self.assertNotIn('original-private-password', str(job.snapshot))
        self.assertNotIn('secret', job.snapshot)
        self.assertEqual(instance.events.filter(type='action.submitted').count(), 1)
        self.assertFalse(instance.events.filter(type='action.executed').exists())
        with self.assertRaises(WorkflowConflict):
            self.engine.approve(final_task, self.alice)
        ticket.refresh_from_db()
        self.assertIsNone(self.plugin.on_approved(instance, ticket))
        self.assertEqual(AutomationExecution.objects.filter(pk=ticket.pk).count(), 1)
        self.assertEqual(self.plugin.get_result(ticket, self.applicant)['state'], 'queued')

    def test_approval_rollback_cannot_publish_a_job(self):
        ticket, instance = self.request_ticket()
        with patch('tickets.tasks.execute_ticket_change_secret.delay') as delay:
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError), transaction.atomic():
                    self.engine.approve(self.task(instance), self.alice)
                    raise RuntimeError('Rollback approval')
            delay.assert_not_called()
        self.assertFalse(AutomationExecution.objects.filter(pk=ticket.pk).exists())

    def test_legacy_tickets_remain_approval_only(self):
        build_context = self.plugin.build_context

        def legacy_context(ticket):
            context = build_context(ticket)
            context.pop('change_secret_version')
            return context

        with patch.object(self.plugin, 'build_context', side_effect=legacy_context):
            ticket, instance = self.request_ticket()
        self.engine.approve(self.task(instance), self.alice)
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'approved')
        self.assertEqual(self.plugin.get_execution_mode(ticket), 'approval_only')
        self.assertEqual(self.plugin.get_result(ticket, self.applicant)['state'], 'approval_only')
        self.assertFalse(AutomationExecution.objects.filter(pk=ticket.pk).exists())

    def test_rejection_and_withdrawal_do_not_create_jobs(self):
        ticket, instance = self.request_ticket()
        self.engine.reject(self.task(instance), self.alice)
        self.assertFalse(AutomationExecution.objects.filter(pk=ticket.pk).exists())
        ticket, instance = self.request_ticket()
        self.engine.cancel(instance, self.applicant)
        self.assertFalse(AutomationExecution.objects.filter(pk=ticket.pk).exists())

    def test_request_rejects_credentials_and_ineligible_accounts(self):
        for name, values in {
            'disabled': {'is_active': False}, 'protected': {'secret_reset': False},
            'key': {'secret_type': SecretType.SSH_KEY},
        }.items():
            Account.objects.create(asset=self.asset, name=name, username=name, **values)
        serializer = self.plugin.get_request_serializer(context={
            'org_id': self.org.id, 'request': SimpleNamespace(user=self.applicant),
        })
        self.assertEqual(serializer.account_options(self.asset.pk), ['service'])
        for parameters in ({'secret': 'do-not-store'}, {'accounts': ['disabled']}, {'accounts': ['protected']},
                           {'accounts': ['key']}, {'accounts': ['@ALL']}):
            payload = self.payload('change_secret', **{
                'asset': str(self.asset.pk), 'accounts': ['service'], **parameters,
            })
            request = self.serializer(payload)
            self.assertFalse(request.is_valid(), parameters)

    def test_submission_enforces_license_platform_and_secure_mode(self):
        payload = self.payload('change_secret', asset=str(self.asset.pk), accounts=['service'])
        with override_settings(XPACK_LICENSE_IS_VALID=False):
            self.assertFalse(self.serializer(payload).is_valid())
        Account.objects.filter(pk=self.account.pk).update(privileged=True)
        with override_settings(CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED=True):
            self.assertFalse(self.serializer(payload).is_valid())
        PlatformAutomation.objects.filter(platform=self.platform).update(change_secret_enabled=False)
        self.assertFalse(self.serializer(payload).is_valid())
        for method in (None, ''):
            PlatformAutomation.objects.filter(platform=self.platform).update(
                change_secret_enabled=True, change_secret_method=method,
            )
            self.assertFalse(self.serializer(payload).is_valid())

    def test_final_approval_rechecks_frozen_account_ids(self):
        ticket, instance = self.request_ticket()
        self.account.delete()
        Account.objects.create(asset=self.asset, name='replacement', username='service')
        self.engine.approve(self.task(instance), self.alice)
        instance.refresh_from_db()
        self.assertEqual(instance.state, 'error')
        self.assertFalse(AutomationExecution.objects.filter(pk=ticket.pk).exists())

    def test_failed_publication_is_durable_and_periodically_retried(self):
        ticket, _ = self.request_ticket(approved=True)
        with patch('tickets.tasks.execute_ticket_change_secret.delay', side_effect=OSError('broker unavailable')):
            dispatch_execution(ticket.pk)
        job = AutomationExecution.objects.get(pk=ticket.pk)
        self.assertEqual(job.status, 'pending')
        with patch('tickets.tasks.execute_ticket_change_secret.delay') as delay:
            dispatch_ticket_change_secrets.run()
            delay.assert_not_called()
            job.result = {'dispatch_after': (timezone.now() - timedelta(seconds=1)).isoformat()}
            job.save(update_fields=['result'])
            dispatch_ticket_change_secrets.run()
            dispatch_ticket_change_secrets.run()
            delay.assert_called_once_with(str(ticket.pk))

    def test_duplicate_delivery_runs_pam_once_and_never_exposes_secrets(self):
        ticket, _ = self.request_ticket(approved=True)

        def run(job):
            self.assertEqual(job.snapshot['accounts'], [str(self.account.pk)])
            ChangeSecretRecord.objects.create(account=self.account, asset=self.asset, execution=job,
                                               status='success', old_secret='old-private', new_secret='new-private')
            job.status, job.date_finished = 'success', timezone.now()
            job.save(update_fields=['status', 'date_finished'])

        with patch.object(AutomationExecution, 'start', autospec=True, side_effect=run) as start:
            execute(str(ticket.pk), 'worker-task-1', 'worker-1')
            execute(str(ticket.pk), 'worker-task-2', 'worker-2')
            start.assert_called_once()
        job = AutomationExecution.objects.get(pk=ticket.pk)
        self.assertEqual(job.snapshot['celery_task_id'], 'worker-task-1')
        result = self.plugin.get_result(ticket, self.applicant)
        self.assertEqual(result['state'], 'success')
        self.assertFalse(result['processing'])
        self.assertEqual(result['counts']['success'], 1)
        data = str(TicketSerializer(ticket, context={
            'request': SimpleNamespace(user=self.applicant), 'view': SimpleNamespace(action='retrieve'),
        }).data)
        for secret in ('old-private', 'new-private', 'original-private-password'):
            self.assertNotIn(secret, data)
        self.assertNotIn('url', result)

    def test_worker_rechecks_scope_and_eligibility_before_running(self):
        for changes in ({'is_active': False}, {'secret_reset': False}, {'username': 'renamed'},
                        {'org_id': self.other_org.id}, {'secret_type': SecretType.SSH_KEY}):
            with self.subTest(changes=changes), transaction.atomic():
                ticket, _ = self.request_ticket(approved=True)
                Account.objects.filter(pk=self.account.pk).update(**changes)
                with patch.object(AutomationExecution, 'start') as start:
                    execute(str(ticket.pk), 'worker-task', 'worker')
                    start.assert_not_called()
                self.assertEqual(self.plugin.get_result(ticket, self.applicant)['state'], 'failed')
                transaction.set_rollback(True)

    def test_worker_rechecks_license_and_applicant(self):
        ticket, _ = self.request_ticket(approved=True)
        with override_settings(XPACK_LICENSE_IS_VALID=False), patch.object(AutomationExecution, 'start') as start:
            execute(str(ticket.pk), 'worker-task', 'worker')
            start.assert_not_called()
        self.assertEqual(AutomationExecution.objects.get(pk=ticket.pk).status, 'error')
        ticket, _ = self.request_ticket(approved=True)
        self.applicant.is_active = False
        self.applicant.save(update_fields=['is_active'])
        with patch.object(AutomationExecution, 'start') as start:
            execute(str(ticket.pk), 'worker-task', 'worker')
            start.assert_not_called()

    def test_failure_and_unverified_results_are_not_reported_as_success(self):
        ticket, _ = self.request_ticket(approved=True)
        with patch.object(AutomationExecution, 'start', side_effect=RuntimeError('sensitive-runner-output')), \
                self.assertLogs('jumpserver.tickets.plugins.change_secret.execution', level='ERROR') as logs:
            execute(str(ticket.pk), 'worker-task', 'worker')
        self.assertNotIn('sensitive-runner-output', str(logs.output))
        self.assertEqual(self.plugin.get_result(ticket, self.applicant)['state'], 'failed')
        self.assertNotIn('sensitive-runner-output', str(self.plugin.get_result(ticket, self.applicant)))
        job = AutomationExecution.objects.get(pk=ticket.pk)
        ChangeSecretRecord.objects.create(account=self.account, asset=self.asset, execution=job,
                                           status='unverified', new_secret='private')
        result = self.plugin.get_result(ticket, self.applicant)
        self.assertEqual(result['state'], 'unverified')
        self.assertEqual(result['counts']['unverified'], 1)
        with tmp_to_org(self.other_org):
            self.assertEqual(self.plugin.get_result(ticket, self.applicant)['state'], 'unverified')

    def test_result_links_require_execution_permission_in_the_ticket_organization(self):
        ticket, _ = self.request_ticket(approved=True)
        job = AutomationExecution.objects.get(pk=ticket.pk)
        task_id = '826f297d-8892-4176-af1b-664d39dbb8b0'
        permission = Permission.objects.get(codename='view_changesecretexecution')
        role = Role.objects.create(name='View ticket password execution', scope='org')
        role.permissions.add(permission)
        RoleBinding.objects_raw.create(user=self.applicant, role=role, org=self.other_org, scope='org')
        self.applicant.expire_rbac_perms_cache()
        with tmp_to_org(self.other_org):
            self.assertNotIn('log_task_id', self.plugin.get_result(ticket, self.applicant))
        job.snapshot['celery_task_id'] = task_id
        job.save(update_fields=['snapshot'])
        with tmp_to_org(self.other_org):
            self.assertNotIn('log_task_id', self.plugin.get_result(ticket, self.applicant))
        RoleBinding.objects_raw.create(user=self.applicant, role=role, org=self.org, scope='org')
        self.applicant.expire_rbac_perms_cache()
        with tmp_to_org(self.other_org):
            result = self.plugin.get_result(ticket, self.applicant)
        self.assertEqual(result['log_task_id'], task_id)
        self.assertNotEqual(result['log_task_id'], str(ticket.pk))
        self.assertNotIn('url', result)
        with override_settings(XPACK_LICENSE_IS_VALID=False):
            self.assertNotIn('log_task_id', self.plugin.get_result(ticket, self.applicant))
        job.snapshot.pop('celery_task_id')
        job.save(update_fields=['snapshot'])
        self.assertNotIn('log_task_id', self.plugin.get_result(ticket, self.applicant))

    def test_empty_execution_results_cannot_claim_success(self):
        ticket, _ = self.request_ticket(approved=True)
        AutomationExecution.objects.filter(pk=ticket.pk).update(status='success', date_finished=timezone.now())
        result = self.plugin.get_result(ticket, self.applicant)
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['counts']['pending'], 1)

    def test_worker_uses_the_pam_manager_without_inheriting_the_approving_task(self):
        with patch('assets.tasks.common.current_task', SimpleNamespace(
            request=SimpleNamespace(id='approving-task', hostname='approval-worker'),
        )):
            ticket, _ = self.request_ticket(approved=True)
        job = AutomationExecution.objects.get(pk=ticket.pk)
        self.assertNotIn('celery_task_id', job.snapshot)
        self.assertNotIn('celery_worker_hostname', job.snapshot)
        with patch('accounts.automations.change_secret.manager.ChangeSecretManager.run', autospec=True) as run:
            execute(str(ticket.pk), 'execution-task', 'ansible-worker')
            run.assert_called_once()
            manager = run.call_args.args[0]
            self.assertEqual(manager.account_ids, [str(self.account.pk)])
            self.assertEqual(manager.secret_strategy, SecretStrategy.random)
            self.assertEqual(manager.secret_type, SecretType.PASSWORD)


@override_settings(XPACK_LICENSE_IS_VALID=True, TICKET_APPLY_ASSET_SCOPE='all',
                   CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED=False)
@skipUnlessDBFeature('has_select_for_update')
class ChangeSecretConcurrencyTests(TransactionTestCase):
    workflow = ChangeSecretTests.workflow
    task = ChangeSecretTests.task
    payload = ChangeSecretTests.payload
    serializer = ChangeSecretTests.serializer
    request_ticket = ChangeSecretTests.request_ticket

    def test_simultaneous_deliveries_start_one_execution(self):
        from tickets.tests.test_workflow_concurrency import WorkflowConcurrencyTests
        helpers.TicketPluginTests.setUpTestData.__func__(type(self))
        ChangeSecretTests.setUp(self)
        with patch('tickets.workflow.business.deliver_event'), patch('tickets.tasks.execute_ticket_change_secret.delay'):
            ticket, _ = self.request_ticket(approved=True)

        def run(job):
            job.status, job.date_finished = 'success', timezone.now()
            job.save(update_fields=['status', 'date_finished'])

        with patch.object(AutomationExecution, 'start', autospec=True, side_effect=run) as start:
            WorkflowConcurrencyTests.race(self, [
                lambda: execute(str(ticket.pk), 'worker-1', 'host-1'),
                lambda: execute(str(ticket.pk), 'worker-2', 'host-2'),
            ])
            start.assert_called_once()
