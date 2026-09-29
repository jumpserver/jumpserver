from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
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
from tickets.models import ApplyAssetTicket, Ticket, TicketStep, TicketAssignee, Workflow, WorkflowInstance, ApprovalTask
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
        ticket = ApplyAssetTicket.objects.create(
            title='Access request', applicant=self.applicant, org_id=self.org.id,
            workflow=workflow or self.workflow(), apply_permission_name=str(uuid4()),
            apply_accounts=['root'], apply_actions=2, apply_date_start=timezone.now(),
            apply_date_expired=timezone.now() + timedelta(hours=2), **kwargs,
        )
        ticket.apply_nodes.add(self.node)
        return ticket

    def task(self, instance, user=None):
        return ApprovalTask.objects.get(node_instance__instance=instance, assignee=user or self.alice, state='pending')

    def test_asset_grant_uses_snapshot_and_only_final_approval(self):
        ticket = self.ticket(self.workflow(levels=2))
        instance = submit_ticket(ticket)
        self.assertFalse(ticket.ticket_steps.exists())
        self.engine.approve(self.task(instance), self.alice)
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
        self.later_asset.nodes.add(self.node)
        ApplyAssetTicket.objects.filter(pk=ticket.pk).update(apply_accounts=['administrator'], apply_actions=128)
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

    def test_manager_and_owner_are_frozen_at_submission(self):
        User.objects.filter(pk=self.applicant.pk).update(manager=self.alice)
        self.applicant.refresh_from_db()
        definition = approval_definition([self.alice], levels=2)
        definition['nodes'][1]['config']['approvers'] = {'type': 'applicant_manager'}
        definition['nodes'][2]['config']['approvers'] = {'type': 'asset_owner'}
        ticket = self.ticket(self.workflow(definition=definition))
        instance = submit_ticket(ticket)
        User.objects.filter(pk=self.applicant.pk).update(manager=self.bob)
        Asset.objects.filter(pk=self.asset.pk).update(owner=self.bob)
        self.engine.approve(self.task(instance), self.alice)
        self.assertEqual(self.task(instance).assignee_id, self.alice.pk)
        self.assertEqual(instance.context['applicant']['manager_id'], str(self.alice.pk))

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

    def test_login_asset_acl_activates_connection_token(self):
        ticket = LoginAssetACL.create_login_asset_review_ticket(
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
        from tickets.notifications import TicketAppliedToAssigneeMessage
        from django.core.cache import cache
        message = TicketAppliedToAssigneeMessage(self.alice, ticket, task_id=task.pk)
        message.get_html_context()
        self.assertEqual(cache.get(message.token)['task_id'], str(task.pk))
        self.engine.approve(task, self.alice)
        with self.assertRaises(WorkflowConflict):
            ticket.approve(self.alice, task_id=task.pk)
        self.assertEqual(self.task(instance).state, 'pending')
        cache.delete(message.token)

    def api_request(self, view, action, user, *, data=None, pk=None, method='get', can_audit=False):
        request = getattr(APIRequestFactory(), method)('/api/v1/tickets/', data or {}, format='json')
        force_authenticate(request, user)
        with transaction.atomic(), patch.object(User, 'has_perm', return_value=can_audit):
            return view.as_view({method: action}, **getattr(getattr(view, action), 'kwargs', {}))(request, **({'pk': str(pk)} if pk else {}))

    def test_options_are_scoped_and_do_not_require_definition_permission(self):
        flow = self.workflow()
        allowed = self.api_request(WorkflowViewSet, 'options_list', self.applicant, data={'org_id': self.org.id})
        self.assertEqual(allowed.status_code, 200, allowed.data)
        self.assertEqual(allowed.data[0]['id'], str(flow.pk))
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
            'name': 'Selected workflow ACL', 'action': 'review', 'workflow': str(workflow.pk),
            'reviewers': [], 'rules': {}, 'users': {'type': 'all'}, 'assets': {'type': 'all'}, 'accounts': ['root'],
        })
        with patch('acls.serializers.base.settings.XPACK_LICENSE_IS_VALID', True):
            # Action choices are materialized lazily when validation accesses fields.
            self.assertTrue(serializer.is_valid(), serializer.errors)
        acl = serializer.save()
        self.assertEqual(acl.workflow_id, workflow.pk)
        self.assertEqual(serializer.data['workflow'], str(workflow.pk))

    def test_all_ticket_serializers_expose_instance_and_exact_tasks(self):
        from tickets.serializers import TicketSerializer, LoginAssetReviewSerializer
        ticket = LoginAssetACL.create_login_asset_review_ticket(self.applicant, self.asset, 'root', [self.alice], self.org.id)
        context = {'request': SimpleNamespace(user=self.alice)}
        for serializer in [TicketSerializer, LoginAssetReviewSerializer]:
            data = serializer(ticket, context=context).data
            self.assertEqual(data['workflow_instance'], str(WorkflowInstance.objects.get(ticket=ticket).pk))
            self.assertEqual(len(data['my_tasks']), 1)
            self.assertEqual(str(data['workflow']['id']), str(ticket.workflow_id))

    def test_invalid_legacy_pending_ticket_is_closed_without_effects(self):
        ticket = self.ticket()
        ticket.apply_nodes.clear()
        step = TicketStep.objects.create(ticket=ticket, state='pending', status='active')
        TicketAssignee.objects.create(step=step, assignee=self.alice)
        result, warnings = import_ticket(ticket.pk, apply=True)
        self.assertEqual(result, 'IMPORTED (error)')
        self.assertTrue(warnings)
        ticket.refresh_from_db()
        self.assertEqual((ticket.state, ticket.status), ('error', 'closed'))
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_submit_endpoint_is_atomic_and_old_decision_endpoint_disabled(self):
        from tickets.api.ticket import ApplyAssetTicketViewSet
        workflow = self.workflow()
        payload = {'title': 'API request', 'workflow_id': str(workflow.pk), 'org_id': self.org.id,
                   'apply_assets': [str(self.asset.pk)], 'apply_accounts': ['root'], 'apply_actions': ['connect'],
                   'apply_date_start': timezone.now(), 'apply_date_expired': timezone.now() + timedelta(hours=1)}
        response = self.api_request(ApplyAssetTicketViewSet, 'open', self.applicant, data=payload, method='post', can_audit=True)
        self.assertEqual(response.status_code, 201, response.data)
        ticket = ApplyAssetTicket.objects.get(pk=response.data['id'])
        self.assertEqual(response.data['workflow_instance'], str(ticket.workflow_instance.pk))
        denied = self.api_request(ApplyAssetTicketViewSet, 'approve', self.alice, pk=ticket.pk, method='put', data={'apply_accounts': ['administrator']})
        self.assertEqual(denied.status_code, 405, denied.data)
        invalid = self.workflow(approvers={'type': 'asset_owner'})
        Asset.objects.filter(pk=self.asset.pk).update(owner=None)
        previous = Ticket.objects.count()
        response = self.api_request(ApplyAssetTicketViewSet, 'open', self.applicant, data={**payload, 'workflow_id': str(invalid.pk)}, method='post', can_audit=True)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Ticket.objects.count(), previous)

    def test_all_accounts_expands_before_conditions_and_does_not_grant_future_names(self):
        from accounts.models import Account
        from tickets.workflow.conditions import evaluate_condition
        Account.objects.create(asset=self.asset, name='root', username='root', secret='workflow-test-secret')
        ticket = self.ticket()
        ticket.apply_accounts = ['@ALL']
        ticket.save(update_fields=['apply_accounts'])
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
        ticket.apply_accounts = ['@INPUT']
        ticket.save(update_fields=['apply_accounts'])
        instance = submit_ticket(ticket)
        with self.assertRaises(WorkflowConfigurationError):
            evaluate_condition({'field': 'account.username', 'operator': 'eq', 'value': 'root'}, instance.context)
