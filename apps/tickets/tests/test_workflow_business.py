from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.translation import override
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from acls.models import LoginACL, LoginAssetACL, CommandFilterACL
from acls.serializers.login_asset_acl import LoginAssetACLSerializer
from assets.models import Asset, Node
from authentication.models import ConnectionToken
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from perms.models import AssetPermission
from terminal.models import Session
from tickets.api.workflow import WorkflowViewSet, WorkflowInstanceViewSet, ApprovalTaskViewSet
from tickets.models import Ticket, TicketStep, TicketAssignee, Workflow, WorkflowInstance, ApprovalTask
from tickets.serializers.ticket.apply_asset import ApplyAssetSerializer
from tickets.tests import test_workflow as fixtures
from tickets.tests.test_workflow import approval_definition
from tickets.workflow.business import submit_ticket, submit_system_ticket
from tickets.workflow.engine import WorkflowEngine
from tickets.workflow.errors import WorkflowConfigurationError, WorkflowConflict
from tickets.workflow.migration import import_ticket
from tickets.workflow.publication import publish_workflow
from users.models import User


class WorkflowBusinessTests(TestCase):
    setUpTestData = classmethod(fixtures.WorkflowTests.setUpTestData.__func__)

    def setUp(self):
        scope = tmp_to_org(self.org)
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.engine = WorkflowEngine()
        self.asset = Asset.objects.create(name='Requested asset', address='192.0.2.10', platform=self.platform, owner=self.alice)
        self.later_asset = Asset.objects.create(name='Added later', address='192.0.2.11', platform=self.platform, owner=self.bob)
        self.node = Node.objects.create(key='900', value='Requested node')
        self.asset.nodes.add(self.node)
        def serial(ticket):
            ticket.serial_num = str(ticket.pk)
            ticket.save(update_fields=['serial_num'])
        self.serial_patch = patch.object(Ticket, 'set_serial_num', serial)
        self.serial_patch.start()
        self.addCleanup(self.serial_patch.stop)

    def workflow(self, ticket_type='apply_asset', definition=None, **config):
        flow = Workflow.objects.create(name=str(uuid4()), type=ticket_type)
        publish_workflow(flow, definition or approval_definition([self.alice], **config))
        flow.refresh_from_db()
        flow.enabled = True
        flow.save(update_fields=['enabled'])
        return flow

    def ticket(self, workflow=None, **kwargs):
        return Ticket.objects.create(
            type='apply_asset', title='Access request', applicant=self.applicant, org_id=self.org.id,
            workflow=workflow or self.workflow(), request_data={
                'apply_permission_name': str(uuid4()), 'apply_nodes': [str(self.node.pk)],
                'apply_accounts': ['root'], 'apply_actions': 2,
                'apply_date_start': timezone.now().isoformat(),
                'apply_date_expired': (timezone.now() + timedelta(hours=2)).isoformat(),
                'apply_expire_soon_notice_minutes': None,
            }, **kwargs,
        )

    def task(self, instance, user=None):
        return ApprovalTask.objects.get(node_instance__instance=instance, assignee=user or self.alice, state='pending')

    def test_asset_grant_uses_snapshot_and_only_final_approval(self):
        ticket = self.ticket(self.workflow(levels=2))
        instance = submit_ticket(ticket)
        self.assertFalse(ticket.ticket_steps.exists())
        self.engine.approve(self.task(instance), self.alice)
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
        self.later_asset.nodes.add(self.node)
        Ticket.objects.filter(pk=ticket.pk).update(
            request_data={**ticket.request_data, 'apply_accounts': ['administrator'], 'apply_actions': 128})
        self.engine.approve(self.task(instance), self.alice)
        ticket.refresh_from_db()
        self.assertEqual((ticket.state, ticket.status), ('approved', 'closed'))
        grant = AssetPermission.objects.get(pk=ticket.pk)
        self.assertEqual(grant.accounts, ['root'])
        self.assertEqual(grant.actions, 2)
        self.assertEqual(list(grant.assets.values_list('pk', flat=True)), [self.asset.pk])
        self.assertFalse(grant.nodes.exists())
        self.assertEqual(list(grant.users.values_list('pk', flat=True)), [self.applicant.pk])
        self.assertEqual(instance.events.filter(type='action.executed').count(), 1)

    def test_deleted_asset_rolls_back_effect_and_records_error(self):
        ticket = self.ticket()
        instance = submit_ticket(ticket)
        self.asset.delete()
        self.assertEqual(self.engine.approve(self.task(instance), self.alice).state, 'error')
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'error')
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
        self.assertFalse(instance.events.filter(type='workflow.completed', data__state='approved').exists())

    def test_permission_failure_rolls_back_partial_permission_and_vote(self):
        ticket = self.ticket()
        instance = submit_ticket(ticket)
        task = self.task(instance)
        with patch('tickets.workflow.business.apply_approved_effect', side_effect=RuntimeError('database unavailable')):
            with self.assertRaises(RuntimeError):
                self.engine.approve(task, self.alice)
        task.refresh_from_db()
        self.assertEqual(task.state, 'pending')
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_expiry_and_withdrawal_close_ticket_without_grant(self):
        for operation in ('expire', 'cancel'):
            ticket = self.ticket(self.workflow(timeout=1))
            instance = submit_ticket(ticket)
            if operation == 'expire':
                instance.node_instances.filter(state='running').update(deadline=timezone.now() - timedelta(seconds=1))
                self.engine.expire(instance)
            else:
                self.engine.cancel(instance, self.applicant)
            ticket.refresh_from_db()
            self.assertEqual(ticket.status, 'closed')
            self.assertEqual(ticket.state, 'expired' if operation == 'expire' else 'closed')
            self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_asset_owner_is_frozen_at_submission(self):
        definition = approval_definition([self.alice], levels=2)
        definition['nodes'][2]['config']['approvers'] = {'type': 'asset_owner'}
        ticket = self.ticket(self.workflow(definition=definition))
        instance = submit_ticket(ticket)
        Asset.objects.filter(pk=self.asset.pk).update(owner=self.bob)
        self.engine.approve(self.task(instance), self.alice)
        self.assertEqual(self.task(instance).assignee_id, self.alice.pk)
        self.assertNotIn('manager_id', instance.context['applicant'])

    def test_login_acl_uses_new_engine_in_global_scope(self):
        acl = LoginACL.objects.create(name='Workflow login ACL', action='review')
        acl.reviewers.add(self.alice)
        ticket = acl.create_confirm_ticket(None, self.applicant)
        with tmp_to_root_org():
            instance = WorkflowInstance.objects.get(ticket=ticket)
            self.assertEqual(instance.org_id, Organization.ROOT_ID)
            self.engine.approve(self.task(instance), self.alice)
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'approved')
        self.assertFalse(ticket.ticket_steps.exists())

    def test_login_poll_after_guard_preserves_authenticated_session(self):
        import time
        from django.conf import settings
        from django.contrib.auth import SESSION_KEY
        from django.urls import reverse

        acl = LoginACL.objects.create(name='Login poll regression', action='review',
                                      users={'type': 'ids', 'ids': [str(self.applicant.pk)]})
        acl.reviewers.add(self.alice)
        ticket = acl.create_confirm_ticket(None, self.applicant)
        session = self.client.session
        session.update({'auth_password': 1, 'user_id': str(self.applicant.pk),
                        'auth_password_expired_at': time.time() + 600,
                        'auth_backend': settings.AUTH_BACKEND_MODEL, 'auth_confirm_required': '1',
                        'auth_acl_id': str(acl.pk), 'auth_ticket_id': str(ticket.pk)})
        session.save()
        url = reverse('api-auth:login-confirm-ticket-status')
        self.assertEqual(self.client.get(url).json()['error'], 'login_confirm_wait')
        with tmp_to_root_org():
            self.engine.approve(self.task(WorkflowInstance.objects.get(ticket=ticket)), self.alice)
        self.assertEqual(self.client.get(url).json(), {'msg': 'ok'})
        self.assertEqual(self.client.get(reverse('authentication:login-guard')).status_code, 302)
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertNotIn('auth_ticket_id', self.client.session)
        self.assertEqual(self.client.get(url).json(), {'msg': 'ok'})
        self.assertIn(SESSION_KEY, self.client.session)

    def test_authenticated_login_poll_still_enforces_pending_review(self):
        from django.contrib.auth import SESSION_KEY
        from django.urls import reverse

        acl = LoginACL.objects.create(name='Pending login review', action='review')
        acl.reviewers.add(self.alice)
        ticket = acl.create_confirm_ticket(None, self.applicant)
        self.client.force_login(self.applicant)
        session = self.client.session
        session.update({'auth_ticket_id': str(ticket.pk), 'auth_confirm_required': '1'})
        session.save()
        url = reverse('api-auth:login-confirm-ticket-status')
        self.assertEqual(self.client.get(url).json()['error'], 'login_confirm_wait')
        with tmp_to_root_org():
            self.engine.reject(self.task(WorkflowInstance.objects.get(ticket=ticket)), self.alice)
        self.assertEqual(self.client.get(url).json()['error'], 'login_confirm_error')
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.client.force_login(self.applicant)
        session = self.client.session
        session.pop('auth_ticket_id', None)
        session['auth_confirm_required'] = '1'
        session.save()
        self.assertEqual(self.client.get(url).json()['error'], 'login_confirm_error')
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_completed_asset_review_displays_actual_reviewers_from_snapshot(self):
        from authentication.services.connection_acl import acl_state
        from authentication.services.connection_acl_batch import create_batch_reviews

        for operation in ('approve', 'reject'):
            with self.subTest(operation=operation):
                rule = LoginAssetACL.objects.create(name=str(uuid4()), action='accept', review_enabled=True)
                rule.reviewers.add(self.alice)
                token = ConnectionToken.objects.create(
                    user=self.applicant, asset=self.asset, account='root', protocol='ssh', connect_method='web_cli',
                    is_active=False, acl_context={'username': 'root', 'review_acls': [str(rule.pk)],
                                                 'requirements': {'review': 'pending'}},
                )
                create_batch_reviews([token])
                self.assertEqual(acl_state(token)['reviewers'][0]['id'], str(self.alice.pk))
                task = self.task(WorkflowInstance.objects.get(ticket=token.from_ticket))
                getattr(self.engine, operation)(task, self.alice)
                rule.reviewers.set([self.bob])
                token.refresh_from_db()
                result = acl_state(token)
                self.assertEqual(result['review_status'], 'approved' if operation == 'approve' else 'rejected')
                self.assertEqual(result['reviewers'], [{
                    'id': str(self.alice.pk), 'name': task.assignee_snapshot['name'],
                    'username': task.assignee_snapshot['username'],
                }])

    def test_login_asset_acl_activates_connection_token(self):
        acl = LoginAssetACL.objects.create(name='Asset review', action='accept', review_enabled=True, review_duration=2)
        ticket = acl.create_login_asset_review_ticket(
            self.applicant, self.asset, 'root', [self.alice], self.org.id,
            workflow=self.workflow('login_asset_confirm'),
        )
        token = ConnectionToken.objects.create(user=self.applicant, asset=self.asset, account='root',
                                                protocol='ssh', connect_method='web_cli', from_ticket=ticket, is_active=False)
        instance = WorkflowInstance.objects.get(ticket=ticket)
        self.engine.approve(self.task(instance), self.alice)
        token.refresh_from_db()
        self.assertTrue(token.is_active)
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'approved')

    def test_command_acl_snapshots_session_asset_and_command(self):
        acl = CommandFilterACL.objects.create(name='Review command', action='review', workflow=self.workflow('command_confirm'))
        session = Session.objects.create(user=str(self.applicant), user_id=str(self.applicant.pk),
                                         asset=str(self.asset), asset_id=str(self.asset.pk), account='root', org_id=self.org.id)
        ticket = acl.create_command_review_ticket('whoami', session, acl, self.org.id)
        instance = WorkflowInstance.objects.get(ticket=ticket)
        self.assertEqual(instance.context['request']['command'], 'whoami')
        self.assertEqual(instance.context['assets'][0]['id'], str(self.asset.pk))
        self.engine.reject(self.task(instance), self.alice)
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'rejected')

    def test_submission_serializer_requires_complete_scoped_resources(self):
        workflow = self.workflow()
        data = {'title': 'Request', 'workflow_id': str(workflow.pk), 'org_id': self.org.id,
                'apply_assets': [str(self.asset.pk)], 'apply_accounts': ['root'], 'apply_actions': ['connect'],
                'apply_date_start': timezone.now(), 'apply_date_expired': timezone.now() + timedelta(hours=1)}
        serializer = ApplyAssetSerializer(data=data, context={'request': SimpleNamespace(user=self.applicant)})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with transaction.atomic():
            ticket = serializer.save()
            submit_ticket(ticket)
        for changes in [{'apply_accounts': []}, {'apply_assets': []}, {'org_id': self.other_org.id}]:
            serializer = ApplyAssetSerializer(data={**data, **changes}, context={'request': SimpleNamespace(user=self.applicant)})
            self.assertFalse(serializer.is_valid())

    def test_migration_preserves_history_and_can_continue_pending_step(self):
        ticket = self.ticket()
        first = TicketStep.objects.create(ticket=ticket, level=1, state='approved', status='closed')
        TicketAssignee.objects.create(step=first, assignee=self.alice, state='approved')
        second = TicketStep.objects.create(ticket=ticket, level=2, state='pending', status='active')
        TicketAssignee.objects.create(step=second, assignee=self.bob)
        Ticket.objects.filter(pk=ticket.pk).update(approval_step=2)
        self.assertEqual(import_ticket(ticket.pk)[0], 'WOULD IMPORT (running)')
        self.assertFalse(WorkflowInstance.objects.filter(ticket=ticket).exists())
        import_ticket(ticket.pk, apply=True)
        instance = WorkflowInstance.objects.get(ticket=ticket)
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
        self.assertEqual(instance.events.filter(type='approval.approved').count(), 1)
        self.engine.approve(self.task(instance, self.bob), self.bob)
        self.assertTrue(AssetPermission.objects.filter(pk=ticket.pk).exists())
        self.assertEqual(import_ticket(ticket.pk, apply=True)[0], 'SKIP')

    def test_migration_keeps_historical_reviewer_display_for_tasks_and_events(self):
        for reviewer in (self.alice, None):
            with self.subTest(reviewer=reviewer):
                ticket = self.ticket()
                step = TicketStep.objects.create(ticket=ticket, state='approved', status='closed')
                display = 'Original reviewer(original-username)'
                old = TicketAssignee.objects.create(step=step, assignee=reviewer, state='approved')
                TicketAssignee.objects.filter(pk=old.pk).update(assignee_display=display)
                Ticket.objects.filter(pk=ticket.pk).update(state='approved', status='closed')
                import_ticket(ticket.pk, apply=True)
                instance = WorkflowInstance.objects.get(ticket=ticket)
                task = instance.node_instances.get(node__type='approval').tasks.get()
                event = instance.events.get(type='approval.approved')
                self.assertEqual(task.assignee_snapshot['display'], display)
                self.assertEqual(event.actor_snapshot, task.assignee_snapshot)
                self.assertEqual(task.assignee_id, reviewer.pk if reviewer else None)
                if reviewer:
                    self.assertEqual(task.assignee_snapshot['name'], reviewer.name)
                    self.assertEqual(task.assignee_snapshot['username'], reviewer.username)

    def test_account_aliases_are_labels_only_in_request_display_and_export(self):
        from tickets.serializers.ticket.ticket import TicketSerializer, TicketRequestItemsField
        ticket = self.ticket()
        selectors = ['@SPEC', 'ops', '@ALL', '@INPUT', '@USER', '@ANON', '@custom']
        ticket.request_data['apply_accounts'] = selectors
        ticket.save(update_fields=['request_data'])
        for imported in (False, True):
            with self.subTest(imported=imported):
                if imported:
                    Ticket.objects.filter(pk=ticket.pk).update(state='approved', status='closed')
                    import_ticket(ticket.pk, apply=True)
                    ticket.refresh_from_db()
                    frozen = deepcopy(ticket.workflow_instance.context)
                with override('zh-hans'):
                    items = TicketSerializer.get_request_items(ticket)
                    accounts = next(item['value'] for item in items if item['name'] == 'apply_accounts')
                    expected = (['匿名账号', '手动输入', '指定账号', '同名账号', '@custom', 'ops'] if imported
                                else ['指定账号', 'ops', '全部', '手动输入', '同名账号', '匿名账号', '@custom'])
                    self.assertEqual(accounts, expected)
                    self.assertIn('指定账号', TicketRequestItemsField().to_file_representation(items))
                ticket.refresh_from_db()
                self.assertEqual(ticket.request_data['apply_accounts'], selectors)
                if imported:
                    self.assertEqual(ticket.workflow_instance.context, frozen)

    def test_legacy_self_assignee_can_approve_or_reject_with_original_policy(self):
        for operation, expected in [('approve', 'approved'), ('reject', 'rejected')]:
            with self.subTest(operation=operation):
                ticket = self.ticket()
                step = TicketStep.objects.create(ticket=ticket, state='pending', status='active')
                TicketAssignee.objects.create(step=step, assignee=self.applicant)
                self.assertEqual(import_ticket(ticket.pk, apply=True), ('IMPORTED (running)', []))
                instance = WorkflowInstance.objects.get(ticket=ticket)
                task = self.task(instance, self.applicant)
                with self.assertRaises(PermissionDenied):
                    self.engine.approve(task, self.alice)
                User.objects.filter(pk=self.applicant.pk).update(is_active=False)
                with self.assertRaises(PermissionDenied):
                    self.engine.approve(task, self.applicant)
                User.objects.filter(pk=self.applicant.pk).update(is_active=True)
                getattr(self.engine, operation)(task, self.applicant)
                ticket.refresh_from_db()
                self.assertEqual((ticket.state, ticket.status), (expected, 'closed'))
                self.assertEqual(AssetPermission.objects.filter(pk=ticket.pk).exists(), operation == 'approve')

    def test_legacy_future_step_preserves_applicant_and_any_approval_strategy(self):
        ticket = self.ticket()
        first = TicketStep.objects.create(ticket=ticket, level=1, state='pending', status='active')
        TicketAssignee.objects.create(step=first, assignee=self.alice)
        second = TicketStep.objects.create(ticket=ticket, level=2, state='pending')
        for user in (self.applicant, self.bob):
            TicketAssignee.objects.create(step=second, assignee=user)
        import_ticket(ticket.pk, apply=True)
        instance = WorkflowInstance.objects.get(ticket=ticket)
        self.engine.approve(self.task(instance), self.alice)
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
        self.engine.approve(self.task(instance, self.applicant), self.applicant)
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'approved')
        self.assertTrue(AssetPermission.objects.filter(pk=ticket.pk).exists())
        self.assertEqual(ApprovalTask.objects.get(node_instance__instance=instance, assignee=self.bob).state,
                         'cancelled')

    def test_new_asset_request_cannot_opt_into_legacy_approval_policy(self):
        ticket = self.ticket(self.workflow(definition=approval_definition(
            [self.applicant, self.alice], exclude_applicant=False)))
        ticket.request_data['legacy'] = {'state': 'pending'}
        ticket.save(update_fields=['request_data'])
        instance = submit_ticket(ticket)
        self.assertNotIn('legacy', instance.context)
        self.assertFalse(ApprovalTask.objects.filter(node_instance__instance=instance,
                                                    assignee=self.applicant).exists())
        old_task = ApprovalTask.objects.create(node_instance=self.task(instance).node_instance,
                                              assignee=self.applicant)
        for operation in ('approve', 'reject'):
            with self.assertRaises(PermissionDenied):
                getattr(self.engine, operation)(old_task, self.applicant)

    def test_legacy_incomplete_context_keeps_request_details_and_export(self):
        from accounts.const import AliasAccount
        from perms.const import ActionChoices
        from tickets.serializers.ticket.ticket import TicketSerializer, TicketRequestItemsField
        for missing in ('applicant', 'asset'):
            with self.subTest(missing=missing):
                ticket = self.ticket()
                ticket.request_data.update(apply_assets=[str(uuid4())], apply_accounts=['@ALL'],
                                           apply_actions=0, apply_expire_soon_notice_minutes=0)
                ticket.state, ticket.status = 'approved', 'closed'
                ticket.rel_snapshot = {'applicant': 'Former applicant', 'apply_assets': ['Deleted host'],
                                       'apply_nodes': ['Original node']}
                if missing == 'applicant':
                    ticket.applicant = None
                ticket.save()
                result, warnings = import_ticket(ticket.pk, apply=True)
                self.assertEqual(result, 'IMPORTED (approved)')
                self.assertTrue(warnings)
                Ticket.objects.filter(pk=ticket.pk).update(rel_snapshot={})
                ticket.refresh_from_db()
                items = TicketSerializer.get_request_items(ticket)
                values = {item['name']: item['value'] for item in items}
                self.assertEqual(values, {
                    'apply_users': ['Former applicant'], 'apply_assets': ['Deleted host'],
                    'apply_nodes': ['Original node'], 'apply_accounts': [str(AliasAccount.ALL.label)],
                    'apply_actions': ActionChoices.display(0),
                    'apply_date_start': ticket.request_data['apply_date_start'],
                    'apply_date_expired': ticket.request_data['apply_date_expired'],
                    'apply_expire_soon_notice_minutes': 0,
                })
                exported = TicketRequestItemsField().to_file_representation(items)
                for value in ('Former applicant', 'Deleted host', 'Original node', str(AliasAccount.ALL.label),
                              ticket.request_data['apply_date_start'], ': 0'):
                    self.assertIn(value, exported)
                self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_asset_request_details_keep_complete_snapshot_after_payload_changes(self):
        from tickets.serializers.ticket.ticket import TicketSerializer
        ticket = self.ticket()
        submit_ticket(ticket)
        ticket.refresh_from_db()
        expected = TicketSerializer.get_request_items(ticket)
        Ticket.objects.filter(pk=ticket.pk).update(request_data={}, rel_snapshot={'apply_nodes': ['Changed']})
        ticket.refresh_from_db()
        self.assertEqual(TicketSerializer.get_request_items(ticket), expected)
        self.assertIsNone(next(item['value'] for item in expected
                               if item['name'] == 'apply_expire_soon_notice_minutes'))

    def test_completed_migration_never_regrants_access(self):
        ticket = self.ticket()
        step = TicketStep.objects.create(ticket=ticket, state='approved', status='closed')
        TicketAssignee.objects.create(step=step, assignee=self.alice, state='approved')
        Ticket.objects.filter(pk=ticket.pk).update(state='approved', status='closed')
        with patch('tickets.workflow.business.apply_approved_effect') as effect:
            import_ticket(ticket.pk, apply=True)
            effect.assert_not_called()
        self.assertEqual(WorkflowInstance.objects.get(ticket=ticket).state, 'approved')
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_notifications_bind_to_task_and_only_publish_after_commit(self):
        ticket = self.ticket(self.workflow(levels=2))
        with patch('tickets.workflow.business.deliver_event') as deliver:
            with self.captureOnCommitCallbacks(execute=True):
                instance = submit_ticket(ticket)
                deliver.assert_not_called()
            deliver.assert_called_once()
        task = self.task(instance)
        from common.auth.cache import TICKET_DIRECT_APPROVE_KEY
        from tickets.notifications import TicketAppliedToAssigneeMessage
        from django.core.cache import cache
        message = TicketAppliedToAssigneeMessage(self.alice, ticket, task_id=task.pk)
        message.get_html_context()
        cache_key = TICKET_DIRECT_APPROVE_KEY.format(token=message.token)
        self.assertEqual(cache.get(cache_key)['task_id'], str(task.pk))
        self.engine.approve(task, self.alice)
        with self.assertRaises(WorkflowConflict):
            ticket.approve(self.alice, task_id=task.pk)
        self.assertEqual(self.task(instance).state, 'pending')
        cache.delete(cache_key)

    def api_request(self, view, action, user, *, data=None, pk=None, method='get', can_audit=False):
        request = getattr(APIRequestFactory(), method)('/api/v1/tickets/', data or {}, format='json')
        force_authenticate(request, user)
        with transaction.atomic(), patch.object(User, 'has_perm', return_value=can_audit):
            return view.as_view({method: action}, **getattr(getattr(view, action), 'kwargs', {}))(request, **({'pk': str(pk)} if pk else {}))

    def test_options_are_scoped_and_do_not_require_definition_permission(self):
        flow = self.workflow()
        allowed = self.api_request(WorkflowViewSet, 'options_list', self.applicant, data={'org_id': self.org.id})
        self.assertEqual(allowed.status_code, 200, allowed.data)
        self.assertIn(str(flow.pk), {item['id'] for item in allowed.data})
        denied = self.api_request(WorkflowViewSet, 'options_list', self.outsider, data={'org_id': self.org.id})
        self.assertEqual(denied.status_code, 403)

    def test_cc_can_read_instance_but_cannot_decide(self):
        definition = approval_definition([self.alice], levels=2)
        definition['nodes'].insert(2, {'id': 'notify', 'type': 'cc', 'config': {
            'users': [str(self.carol.pk)],
        }})
        definition['edges'] = [['start', 'approval_0'], ['approval_0', 'notify'],
                               ['notify', 'approval_1'], ['approval_1', 'end']]
        workflow = self.workflow(definition=definition)
        ticket = self.ticket(workflow)
        instance = submit_ticket(ticket)
        self.assertFalse(ticket.cc_users.filter(pk=self.carol.pk).exists())
        before = self.api_request(WorkflowInstanceViewSet, 'retrieve', self.carol, pk=instance.pk)
        self.assertEqual(before.status_code, 404)
        self.engine.approve(self.task(instance), self.alice)
        self.assertTrue(ticket.cc_users.filter(pk=self.carol.pk).exists())
        cc_event = instance.events.get(type='cc.added')
        self.assertEqual([item['id'] for item in cc_event.data['recipients']], [str(self.carol.pk)])
        from tickets.workflow.business import deliver_event
        with patch('tickets.notifications.TicketUpdatedToCcUserMessage.publish_async') as notify:
            deliver_event(cc_event.pk)
            notify.assert_called_once()
        allowed = self.api_request(WorkflowInstanceViewSet, 'retrieve', self.carol, pk=instance.pk)
        self.assertEqual(allowed.status_code, 200, allowed.data)
        denied = self.api_request(ApprovalTaskViewSet, 'approve', self.carol, pk=self.task(instance).pk, method='post')
        self.assertEqual(denied.status_code, 404)

    def test_reassignment_candidates_and_decisions_are_scoped(self):
        ticket = self.ticket(self.workflow(allow_transfer=True))
        instance = submit_ticket(ticket)
        task = self.task(instance)
        response = self.api_request(ApprovalTaskViewSet, 'candidates', self.alice, pk=task.pk)
        self.assertEqual(response.status_code, 200, response.data)
        ids = {str(user['id']) for user in response.data['results']}
        self.assertIn(str(self.bob.pk), ids)
        self.assertNotIn(str(self.outsider.pk), ids)
        self.assertNotIn(str(self.applicant.pk), ids)
        denied = self.api_request(ApprovalTaskViewSet, 'transfer', self.alice, pk=task.pk, method='post', data={'target': str(self.outsider.pk)})
        self.assertEqual(denied.status_code, 400)
        result = self.api_request(ApprovalTaskViewSet, 'transfer', self.alice, pk=task.pk, method='post', data={'target': str(self.bob.pk), 'comment': 'Specialist review'})
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(self.task(instance, self.bob).state, 'pending')

    def test_acl_serializer_accepts_workflow_without_reviewers(self):
        workflow = self.workflow('login_asset_confirm')
        serializer = LoginAssetACLSerializer(data={
            'name': 'Selected workflow ACL', 'action': 'accept', 'review_enabled': True, 'workflow': str(workflow.pk),
            'reviewers': [], 'rules': {}, 'users': {'type': 'all'}, 'assets': {'type': 'all'}, 'accounts': ['root'],
        })
        with patch('acls.serializers.base.settings.XPACK_LICENSE_IS_VALID', True):
            # Action choices are materialized lazily when validation accesses fields.
            self.assertTrue(serializer.is_valid(), serializer.errors)
        acl = serializer.save()
        self.assertEqual(acl.workflow_id, workflow.pk)
        self.assertEqual(serializer.data['workflow'], str(workflow.pk))

    def test_ticket_serializer_exposes_instance_and_exact_tasks(self):
        from tickets.serializers import TicketSerializer
        acl = LoginAssetACL.objects.create(name='Asset review', action='accept', review_enabled=True, review_duration=2)
        acl.reviewers.add(self.alice)
        ticket = acl.create_login_asset_review_ticket(self.applicant, self.asset, 'root', [self.alice], self.org.id)
        context = {'request': SimpleNamespace(user=self.alice)}
        data = TicketSerializer(ticket, context=context).data
        self.assertEqual(data['workflow_instance'], str(WorkflowInstance.objects.get(ticket=ticket).pk))
        self.assertEqual(len(data['my_tasks']), 1)
        self.assertEqual(str(data['workflow']['id']), str(ticket.workflow_id))

    def test_invalid_legacy_pending_ticket_is_closed_without_effects(self):
        ticket = self.ticket()
        ticket.request_data['apply_nodes'] = []
        ticket.save(update_fields=['request_data'])
        step = TicketStep.objects.create(ticket=ticket, state='pending', status='active')
        TicketAssignee.objects.create(step=step, assignee=self.alice)
        result, warnings = import_ticket(ticket.pk, apply=True)
        self.assertEqual(result, 'IMPORTED (error)')
        self.assertTrue(warnings)
        ticket.refresh_from_db()
        self.assertEqual((ticket.state, ticket.status), ('error', 'closed'))
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_submit_endpoint_is_atomic_and_old_decision_endpoint_disabled(self):
        from tickets.api.ticket import TicketViewSet
        workflow = self.workflow()
        payload = {'type': 'apply_asset', 'title': 'API request', 'workflow_id': str(workflow.pk), 'org_id': self.org.id,
                   'request_data': {
                       'apply_assets': [str(self.asset.pk)], 'apply_accounts': ['root'], 'apply_actions': ['connect'],
                       'apply_date_start': timezone.now(), 'apply_date_expired': timezone.now() + timedelta(hours=1),
                   }}
        response = self.api_request(TicketViewSet, 'open', self.applicant, data=payload, method='post', can_audit=True)
        self.assertEqual(response.status_code, 201, response.data)
        ticket = Ticket.objects.get(pk=response.data['id'])
        self.assertEqual(response.data['workflow_instance'], str(ticket.workflow_instance.pk))
        denied = self.api_request(TicketViewSet, 'approve', self.alice, pk=ticket.pk, method='put', data={'apply_accounts': ['administrator']})
        self.assertEqual(denied.status_code, 405, denied.data)
        invalid = self.workflow(approvers={'type': 'asset_owner'})
        Asset.objects.filter(pk=self.asset.pk).update(owner=None)
        previous = Ticket.objects.count()
        response = self.api_request(TicketViewSet, 'open', self.applicant, data={**payload, 'workflow_id': str(invalid.pk)}, method='post', can_audit=True)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Ticket.objects.count(), previous)

    def test_all_accounts_expands_before_conditions_and_does_not_grant_future_names(self):
        from accounts.models import Account
        from tickets.workflow.conditions import evaluate_condition
        Account.objects.create(asset=self.asset, name='root', username='root', secret='workflow-test-secret')
        ticket = self.ticket()
        ticket.request_data['apply_accounts'] = ['@ALL']
        ticket.save(update_fields=['request_data'])
        instance = submit_ticket(ticket)
        self.assertTrue(evaluate_condition({'field': 'account.username', 'operator': 'eq', 'value': 'root'}, instance.context))
        import json
        self.assertNotIn('workflow-test-secret', json.dumps(instance.context))
        Account.objects.create(asset=self.asset, name='new-admin', username='new-admin')
        self.engine.approve(self.task(instance), self.alice)
        self.assertEqual(AssetPermission.objects.get(pk=ticket.pk).accounts, ['root'])

    def test_manual_username_cannot_skip_username_policy(self):
        from tickets.workflow.conditions import evaluate_condition
        ticket = self.ticket()
        ticket.request_data['apply_accounts'] = ['@INPUT']
        ticket.save(update_fields=['request_data'])
        instance = submit_ticket(ticket)
        with self.assertRaises(WorkflowConfigurationError):
            evaluate_condition({'field': 'account.username', 'operator': 'eq', 'value': 'root'}, instance.context)

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    def test_login_exemption_starts_only_after_final_commit(self):
        from django.core.cache import cache
        cache.clear()
        acl = LoginAssetACL.objects.create(name='Two approvals', action='accept', review_enabled=True, review_duration=2)
        ticket = acl.create_login_asset_review_ticket(
            self.applicant, self.asset, 'root', [], self.org.id,
            workflow=self.workflow('login_asset_confirm', levels=2),
        )
        instance = WorkflowInstance.objects.get(ticket=ticket)
        self.assertNotIn('login_asset_review', instance.context)
        with self.captureOnCommitCallbacks(execute=True):
            self.engine.approve(self.task(instance), self.alice)
        self.assertFalse(acl.is_review_exempt(self.applicant, self.asset, 'root'))
        with self.captureOnCommitCallbacks(execute=True):
            self.engine.approve(self.task(instance), self.alice)
            self.assertFalse(acl.is_review_exempt(self.applicant, self.asset, 'root'))
        self.assertTrue(acl.is_review_exempt(self.applicant, self.asset, 'root'))
        self.assertFalse(acl.is_review_exempt(self.applicant, self.asset, 'admin'))
        acl.review_duration = 0
        acl.save(update_fields=['review_duration'])
        self.assertFalse(acl.is_review_exempt(self.applicant, self.asset, 'root'))

    def test_auditor_can_read_ticket_and_events_only_in_authorized_org(self):
        from audits.api import TicketAuditViewSet
        from rbac.models import Permission, Role, RoleBinding
        from tickets.api.ticket import TicketViewSet
        ticket = self.ticket()
        instance = submit_ticket(ticket)
        permission = Permission.objects.get(content_type__app_label='audits', codename='view_ticketaudit')
        role = Role.objects.create(name='Ticket auditor', scope='org')
        role.permissions.add(permission)
        RoleBinding.objects_raw.create(user=self.carol, role=role, org=self.org, scope='org')
        self.carol.expire_rbac_perms_cache()

        def request(view, action, pk=None, method='get', data=None):
            user = User.objects.get(pk=self.carol.pk)
            req = getattr(APIRequestFactory(), method)('/api/v1/tickets/', data or {}, format='json')
            force_authenticate(req, user)
            # Match ATOMIC_REQUESTS so a rejected request cannot roll back the test fixture.
            with transaction.atomic():
                return view.as_view({method: action}, **getattr(getattr(view, action), 'kwargs', {}))(
                    req, **({'pk': str(pk)} if pk else {}))

        self.assertEqual(request(TicketAuditViewSet, 'list').status_code, 200)
        detail = request(TicketViewSet, 'retrieve', ticket.pk)
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data['my_tasks'], [])
        self.assertEqual(detail.data['result']['actions'], [])
        self.assertEqual(request(WorkflowInstanceViewSet, 'retrieve', instance.pk).status_code, 200)
        self.assertEqual(request(WorkflowInstanceViewSet, 'events', instance.pk).status_code, 200)
        self.assertEqual(request(ApprovalTaskViewSet, 'approve', self.task(instance).pk, 'post').status_code, 404)
        self.assertEqual(request(WorkflowInstanceViewSet, 'cancel', instance.pk, 'post').status_code, 403)

        with tmp_to_org(self.other_org):
            other = Ticket.objects.create(type='general', title='Other organization', applicant=self.outsider)
            own = Ticket.objects.create(type='general', title='Own request elsewhere', applicant=self.carol)
        self.assertEqual(request(TicketViewSet, 'retrieve', other.pk).status_code, 404)
        self.assertEqual(request(TicketViewSet, 'retrieve', own.pk).status_code, 200)
        report = request(TicketAuditViewSet, 'list', data={'format': 'xlsx', 'export_mode': 'report'})
        self.assertEqual(report.status_code, 200)
        from io import BytesIO
        from openpyxl import load_workbook
        workbook = load_workbook(BytesIO(report.content), read_only=True)
        cells = [str(cell) for sheet in workbook for row in sheet.values for cell in row]
        workbook.close()
        self.assertIn(ticket.title, cells)
        self.assertNotIn(other.title, cells)
        self.assertNotIn(own.title, cells)

        with tmp_to_org(self.other_org):
            self.assertIn(request(TicketViewSet, 'retrieve', ticket.pk).status_code, (403, 404))
            self.assertEqual(request(WorkflowInstanceViewSet, 'retrieve', instance.pk).status_code, 404)
            self.assertEqual(request(WorkflowInstanceViewSet, 'events', instance.pk).status_code, 404)

    def test_asset_acl_combines_unique_workflows_before_releasing_connections(self):
        from authentication.services.connection_acl_batch import create_batch_reviews
        from tickets.serializers.ticket import TicketSerializer
        first = self.workflow('login_asset_confirm')
        second = self.workflow('login_asset_confirm', definition=approval_definition(
            [self.bob], strategy='all', timeout=300, allow_transfer=True,
        ))
        rules = [LoginAssetACL.objects.create(
            name=name, action='accept', review_enabled=True, workflow=workflow,
        ) for name, workflow in [('A', first), ('B', first), ('C', second)]]
        tokens = [ConnectionToken.objects.create(
            user=self.applicant, asset=asset, account='root', protocol='ssh',
            connect_method='web_cli', is_active=False,
            acl_context={'username': 'root', 'review_acls': [str(rule.pk) for rule in rules],
                         'requirements': {'review': 'pending', 'push_account': 'pending'}},
        ) for asset in (self.asset, self.later_asset)]
        create_batch_reviews(tokens)
        for token in tokens:
            token.refresh_from_db()
        self.assertEqual(tokens[0].from_ticket_id, tokens[1].from_ticket_id)
        ticket = tokens[0].from_ticket
        instance = WorkflowInstance.objects.get(ticket=ticket)
        self.assertEqual(instance.version.nodes.filter(type='approval').count(), 2)
        self.assertEqual({asset['id'] for asset in instance.context['assets']},
                         {str(self.asset.pk), str(self.later_asset.pk)})
        self.assertEqual(len(TicketSerializer.get_login_asset_connections(ticket)), 2)
        configs = list(instance.version.nodes.filter(type='approval').values_list('config', flat=True))
        self.assertTrue(any(config['strategy'] == 'all' and config['timeout'] == 300 and config['allow_transfer']
                            for config in configs))
        self.engine.approve(self.task(instance, self.alice), self.alice)
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'pending')
        for token in tokens:
            token.refresh_from_db()
            self.assertFalse(token.is_active)
            self.assertEqual(token.acl_context['requirements']['review'], 'pending')
        self.engine.approve(self.task(instance, self.bob), self.bob)
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'approved')
        for token in tokens:
            token.refresh_from_db()
            self.assertEqual(token.acl_context['requirements'], {'review': 'passed', 'push_account': 'pending'})
            self.assertFalse(token.is_active)
        self.assertEqual(first.versions.count(), 1)
        self.assertEqual(second.versions.count(), 1)

    def test_asset_acl_mixed_workflow_and_fixed_reviewers_preserves_both(self):
        workflow = self.workflow('login_asset_confirm')
        first = LoginAssetACL.objects.create(name='A', action='accept', review_enabled=True, workflow=workflow)
        second = LoginAssetACL.objects.create(name='B', action='accept', review_enabled=True)
        second.reviewers.add(self.bob)
        ticket = first.create_login_asset_review_ticket(
            self.applicant, self.asset, 'root', [self.bob], self.org.id, review_acls=[first, second],
        )
        instance = WorkflowInstance.objects.get(ticket=ticket)
        self.engine.approve(self.task(instance, self.alice), self.alice)
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'pending')
        self.engine.reject(self.task(instance, self.bob), self.bob)
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'rejected')

    def test_asset_acl_changed_workflow_cannot_reuse_existing_approval(self):
        from authentication.services.connection_acl import get_pending_review_assignees
        from authentication.services.connection_acl_batch import create_batch_reviews
        flow = self.workflow('login_asset_confirm')
        rule = LoginAssetACL.objects.create(name='Bound workflow', action='accept', review_enabled=True, workflow=flow)
        token = ConnectionToken.objects.create(
            user=self.applicant, asset=self.asset, account='root', protocol='ssh', connect_method='web_cli',
            is_active=False, acl_context={'username': 'root', 'review_acls': [str(rule.pk)],
                                         'requirements': {'review': 'pending'}},
        )
        create_batch_reviews([token])
        self.assertEqual(token.from_ticket.workflow_id, flow.pk)
        publish_workflow(flow, approval_definition([self.bob]))
        with self.assertRaises(PermissionDenied):
            get_pending_review_assignees(token)
        token.refresh_from_db()
        self.assertFalse(token.is_active)

    def test_asset_acl_disabled_workflow_does_not_fall_back_to_reviewers(self):
        flow = self.workflow('login_asset_confirm')
        flow.enabled = False
        flow.save(update_fields=['enabled'])
        rule = LoginAssetACL.objects.create(name='Disabled workflow', action='accept', review_enabled=True, workflow=flow)
        rule.reviewers.add(self.bob)
        with self.assertRaises(WorkflowConfigurationError):
            LoginAssetACL.get_review_assignees([rule])

    def test_legacy_asset_review_uses_original_reviewer_check(self):
        from authentication.services.connection_acl import get_pending_review_assignees
        from authentication.services.connection_acl_batch import create_batch_reviews
        rule = LoginAssetACL.objects.create(name='Fixed reviewers', action='accept', review_enabled=True)
        rule.reviewers.add(self.alice)
        token = ConnectionToken.objects.create(
            user=self.applicant, asset=self.asset, account='root', protocol='ssh', connect_method='web_cli',
            is_active=False, acl_context={'username': 'root', 'review_acls': [str(rule.pk)],
                                         'requirements': {'review': 'pending'}},
        )
        create_batch_reviews([token])
        ticket = token.from_ticket
        ticket.meta.pop('login_asset_review_config')
        ticket.save(update_fields=['meta'])
        self.assertEqual(get_pending_review_assignees(token)[1], [self.alice])
        rule.reviewers.set([self.bob])
        with self.assertRaises(PermissionDenied):
            get_pending_review_assignees(token)

    def test_workflow_review_preview_and_batch_grouping_share_policy_identity(self):
        from authentication.services.connection_acl import acl_state
        from authentication.services.connection_acl_batch import create_batch_reviews
        tokens = []
        for user, workflow in [(self.applicant, self.workflow('login_asset_confirm')),
                               (self.applicant, self.workflow('login_asset_confirm')),
                               (self.bob, self.workflow('login_asset_confirm'))]:
            rule = LoginAssetACL.objects.create(name=str(uuid4()), action='accept', review_enabled=True, workflow=workflow)
            tokens.append(ConnectionToken.objects.create(
                user=user, asset=self.asset, account='root', protocol='ssh', connect_method='web_cli',
                is_active=False, acl_context={'username': 'root', 'review_acls': [str(rule.pk)],
                                             'requirements': {'review': 'pending'}},
            ))
        groups = [acl_state(token)['review_group'] for token in tokens]
        self.assertTrue(all(groups))
        self.assertEqual(len(set(groups)), 3)
        create_batch_reviews(tokens)
        self.assertEqual(len({token.from_ticket_id for token in tokens}), 3)
