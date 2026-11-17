from datetime import timedelta
from importlib import import_module
from unittest.mock import patch
from uuid import uuid4

from django.db import connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase
from django.utils import timezone

from accounts.models import Account
from assets.models import Asset, Node, Platform
from orgs.models import Organization
from orgs.utils import tmp_to_org
from perms.models import AssetPermission
from tickets.models import Ticket, TicketAssignee, TicketStep, Workflow, WorkflowInstance, ApprovalTask
from tickets.tests import test_workflow as fixtures, test_resource_adjustment as resource_fixtures
from tickets.workflow.engine import WorkflowEngine
from tickets.workflow.resources import adjustment_status
from users.models import User


import_ticket = import_module('tickets.migrations.0010_ticket_workflow_refactor').import_ticket


class HistoricalInstanceUpgradeTests(TestCase):
    applicant: User
    alice: User
    bob: User
    org: Organization
    other_org: Organization
    platform: Platform

    setUpTestData = fixtures.WorkflowTests.__dict__['setUpTestData']
    call = resource_fixtures.ResourceAdjustmentTests.call

    def setUp(self):
        scope = tmp_to_org(self.org)
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.alice.expire_rbac_perms_cache()
        self.apps = MigrationLoader(connection).project_state().apps

    def import_ticket(self, ticket):
        historical = self.apps.get_model('tickets', 'Ticket').objects.get(pk=ticket.pk)
        with transaction.atomic():
            return import_ticket(self.apps, 'default', historical)

    def ticket(self, **kwargs):
        return Ticket.objects.create(type='login_confirm', title='Historical upgrade',
                                     applicant=self.applicant, org_id=self.org.pk,
                                     request_data={'apply_login_ip': '192.0.2.24'}, **kwargs)

    def incomplete_asset_ticket(self, levels=1, current=1, **resources):
        ticket = self.ticket(approval_step=current)
        ticket.type = 'apply_asset'
        ticket.request_data = {
            'apply_assets': [], 'apply_nodes': [], 'apply_accounts': [], 'apply_actions': 1,
            'apply_date_start': timezone.now().isoformat(),
            'apply_date_expired': (timezone.now() + timedelta(hours=1)).isoformat(), **resources,
        }
        ticket.save()
        for level in range(1, levels + 1):
            step = TicketStep.objects.create(
                ticket=ticket, level=level, state='approved' if level < current else 'pending',
                status='closed' if level < current else (
                    'active' if level == current else 'pending'))
            TicketAssignee.objects.create(
                step=step, assignee=self.alice if level == current else self.applicant,
                state='approved' if level < current else 'pending', comment='Original review')
        return ticket

    def test_empty_resources_preserve_one_to_five_level_approval_progress(self):
        with patch('tickets.workflow.business.deliver_event'):
            for levels in range(1, 6):
                with self.subTest(levels=levels):
                    current = min(levels, 2)
                    ticket = self.incomplete_asset_ticket(levels, current)
                    original = ticket.request_data
                    self.assertEqual(self.import_ticket(ticket), [])
                    ticket.refresh_from_db()
                    instance = WorkflowInstance.objects.get(ticket=ticket)
                    self.assertEqual((ticket.state, ticket.status, instance.state),
                                     ('pending', 'open', 'running'))
                    self.assertFalse(instance.context.get('resources_pending'))
                    self.assertIsNone(adjustment_status(instance, self.alice))
                    history = list(ApprovalTask.objects.filter(
                        node_instance__instance=instance, state='approved').values('id', 'comment'))
                    self.assertEqual(len(history), current - 1)
                    self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
                    for level in range(current, levels + 1):
                        task = ApprovalTask.objects.get(
                            node_instance__instance=instance, state='pending')
                        reviewer = self.alice if level == current else self.applicant
                        self.assertEqual(task.assignee_id, reviewer.pk)
                        response = self.call(task, user=reviewer, operation='approve')
                        self.assertEqual(response.status_code, 200, response.data)
                    instance.refresh_from_db()
                    ticket.refresh_from_db()
                    self.assertEqual(instance.state, 'approved')
                    self.assertEqual(ticket.request_data, original)
                    self.assertEqual(instance.events.filter(type='approval.approved').count(),
                                     levels)
                    for previous in history:
                        self.assertEqual(ApprovalTask.objects.get(pk=previous['id']).comment,
                                         previous['comment'])
                    permission = AssetPermission.objects.get(pk=ticket.pk)
                    self.assertEqual(permission.accounts, [])
                    self.assertFalse(permission.assets.exists())
                    self.assertFalse(permission.nodes.exists())
                    self.assertEqual(instance.events.filter(type='action.executed').count(), 1)

    def test_partial_legacy_resources_are_granted_without_filling_or_expanding_them(self):
        asset = Asset.objects.create(
            name='Upgrade target', address='192.0.2.24', platform=self.platform)
        node = Node.objects.create(key='502', value='Empty upgrade node')
        for resources in ({'apply_assets': [str(asset.pk)]}, {'apply_accounts': ['root']},
                          {'apply_assets': [str(asset.pk)], 'apply_accounts': ['@ALL']},
                          {'apply_nodes': [str(node.pk)], 'apply_accounts': ['root']}):
            with (self.subTest(resources=resources),
                  patch('tickets.workflow.business.deliver_event')):
                ticket = self.incomplete_asset_ticket(**resources)
                original = ticket.request_data
                self.assertEqual(self.import_ticket(ticket), [])
                instance = WorkflowInstance.objects.get(ticket=ticket)
                task = ApprovalTask.objects.get(node_instance__instance=instance, state='pending')
                WorkflowEngine().approve(task, self.alice)
                ticket.refresh_from_db()
                self.assertEqual(ticket.request_data, original)
                self.assertEqual(ticket.state, 'approved')
                permission = AssetPermission.objects.get(pk=ticket.pk)
                self.assertEqual(permission.accounts, original['apply_accounts'])
                self.assertEqual([str(pk) for pk in permission.assets.values_list('pk', flat=True)],
                                 original['apply_assets'])
                self.assertEqual([str(pk) for pk in permission.nodes.values_list('pk', flat=True)],
                                 original['apply_nodes'])

    def test_legacy_approval_keeps_assignee_and_organization_checks(self):
        ticket = self.incomplete_asset_ticket()
        self.assertEqual(self.import_ticket(ticket), [])
        instance = WorkflowInstance.objects.get(ticket=ticket)
        task = ApprovalTask.objects.get(node_instance__instance=instance, state='pending')
        self.assertEqual(self.call(task, user=self.bob, operation='approve').status_code, 404)
        with tmp_to_org(self.other_org):
            self.assertEqual(self.call(task, operation='approve').status_code, 404)
        self.assertEqual(self.call(task, {
            'resources': {}, 'reason': 'Keep the original request', 'expected_revision': 0,
        }).status_code, 409)
        task.refresh_from_db()
        self.assertEqual(task.state, 'pending')
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_legacy_account_aliases_keep_their_original_meaning(self):
        selectors = ['@USER', '@INPUT', '@ANON', 'manual-account']
        ticket = self.incomplete_asset_ticket(apply_accounts=selectors)
        self.assertEqual(self.import_ticket(ticket), [])
        instance = WorkflowInstance.objects.get(ticket=ticket)
        User.objects.filter(pk=self.applicant.pk).update(username='renamed-applicant')
        task = ApprovalTask.objects.get(node_instance__instance=instance, state='pending')
        with patch('tickets.workflow.business.deliver_event'):
            WorkflowEngine().approve(task, self.alice)
        self.assertEqual(AssetPermission.objects.get(pk=ticket.pk).accounts, selectors)

    def test_legacy_runtime_validation_still_rejects_invalid_resources_and_expiry(self):
        for change in ('asset_org', 'node_org', 'applicant', 'expired'):
            with self.subTest(change=change), patch('tickets.workflow.business.deliver_event'):
                asset = Asset.objects.create(name=str(uuid4()), address='192.0.2.24',
                                             platform=self.platform)
                node = Node.objects.create(key=str(uuid4().int), value='Upgrade node')
                period = {} if change != 'expired' else {
                    'apply_date_start': (timezone.now() - timedelta(days=2)).isoformat(),
                    'apply_date_expired': (timezone.now() - timedelta(days=1)).isoformat(),
                }
                ticket = self.incomplete_asset_ticket(
                    apply_assets=[str(asset.pk)], apply_nodes=[str(node.pk)], **period)
                self.assertEqual(self.import_ticket(ticket), [])
                instance = WorkflowInstance.objects.get(ticket=ticket)
                task = ApprovalTask.objects.get(node_instance__instance=instance, state='pending')
                if change == 'asset_org':
                    Asset.objects.filter(pk=asset.pk).update(org_id=self.other_org.pk)
                elif change == 'node_org':
                    Node.objects.filter(pk=node.pk).update(org_id=self.other_org.pk)
                elif change == 'applicant':
                    User.objects.filter(pk=self.applicant.pk).update(is_active=False)
                WorkflowEngine().approve(task, self.alice)
                instance.refresh_from_db()
                self.assertEqual(instance.state, 'error')
                self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
                User.objects.filter(pk=self.applicant.pk).update(is_active=True)

    def test_invalid_selected_legacy_resources_still_fail_upgrade(self):
        for resources in ({'apply_assets': [str(uuid4())]}, {'apply_nodes': [str(uuid4())]},
                          {'apply_accounts': [1]}, {'apply_accounts': ''}, {'apply_accounts': None},
                          {'apply_date_expired': 'invalid'}, {'apply_actions': 'connect'}):
            with self.subTest(resources=resources):
                ticket = self.incomplete_asset_ticket(**resources)
                self.assertTrue(self.import_ticket(ticket))
                ticket.refresh_from_db()
                self.assertEqual((ticket.state, ticket.status), ('error', 'closed'))
                self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_historical_asset_snapshot_can_finish_pending_approval(self):
        asset = Asset.objects.create(name='Upgrade target', address='192.0.2.24',
                                     platform=self.platform, owner=self.alice)
        Account.objects.bulk_create([Account(name='audit', username='audit', asset=asset, org_id=self.org.pk)])
        node = Node.objects.create(key='501', value='Upgrade parent')
        child = Node.objects.create(key='501:1', value='Upgrade child')
        asset.nodes.add(child)
        ticket = self.ticket()
        ticket.type = 'apply_asset'
        ticket.request_data = {
            'apply_nodes': [str(node.pk)], 'apply_assets': [], 'apply_accounts': ['@ALL'],
            'apply_permission_name': 'Migrated permission', 'apply_actions': 1,
            'apply_date_start': timezone.now().isoformat(),
            'apply_date_expired': (timezone.now() + timedelta(hours=1)).isoformat(),
        }
        ticket.save()
        first = TicketStep.objects.create(ticket=ticket, level=1, state='approved', status='closed')
        TicketAssignee.objects.create(step=first, assignee=self.alice, state='approved')
        second = TicketStep.objects.create(ticket=ticket, level=2, state='pending', status='active')
        TicketAssignee.objects.create(step=second, assignee=self.bob)
        Ticket.objects.filter(pk=ticket.pk).update(approval_step=2)
        self.assertEqual(self.import_ticket(ticket), [])
        instance = WorkflowInstance.objects.get(ticket=ticket)
        self.assertEqual(instance.state, 'running')
        self.assertEqual(instance.context['assets'][0]['owner_ids'], [str(self.alice.pk)])
        self.assertEqual(instance.context['request']['account_selectors'], ['@ALL'])
        self.assertEqual(instance.context['actions'], ['connect'])
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
        task = ApprovalTask.objects.get(node_instance__instance=instance, state='pending')
        with patch('tickets.workflow.business.deliver_event'):
            WorkflowEngine().approve(task, self.bob)
        permission = AssetPermission.objects.get(pk=ticket.pk)
        self.assertFalse(permission.assets.exists())
        self.assertEqual(list(permission.nodes.values_list('pk', flat=True)), [node.pk])
        self.assertEqual(permission.accounts, ['@ALL'])
        later = Asset.objects.create(name='Added after approval', address='192.0.2.26',
                                     platform=self.platform)
        later.nodes.add(child)
        Account.objects.bulk_create([
            Account(name='later', username='later', asset=later, org_id=self.org.pk)])
        self.assertEqual(set(permission.get_all_assets(flat=True)), {asset.pk, later.pk})
        self.assertEqual(set(permission.get_all_accounts().values_list('username', flat=True)),
                         {'audit', 'later'})
        self.assertEqual(list(permission.users.values_list('pk', flat=True)), [self.applicant.pk])
        instance.refresh_from_db()
        self.assertEqual(instance.state, 'approved')
        self.assertEqual(instance.events.filter(type='action.executed').count(), 1)
        self.assertEqual(self.import_ticket(ticket), [])
        self.assertEqual(WorkflowInstance.objects.filter(ticket=ticket).count(), 1)

    def test_deleted_historical_reviewer_snapshot_survives_without_effects(self):
        ticket = self.ticket(state='approved', status='closed')
        step = TicketStep.objects.create(ticket=ticket, level=1, state='approved', status='closed')
        TicketAssignee.objects.create(step=step, assignee=None, state='approved',
                                      assignee_display='Deleted reviewer(old-reviewer)', comment='Approved for audit')
        with patch('tickets.workflow.business.apply_approved_effect') as effect:
            self.assertEqual(self.import_ticket(ticket), [])
        effect.assert_not_called()
        task = ApprovalTask.objects.get(node_instance__instance__ticket=ticket)
        self.assertIsNone(task.assignee_id)
        self.assertEqual(task.comment, 'Approved for audit')
        self.assertEqual(task.assignee_snapshot['display'], 'Deleted reviewer(old-reviewer)')
        self.assertEqual(task.node_instance.instance.events.get(type='approval.approved').actor_snapshot,
                         task.assignee_snapshot)

    def test_closed_pending_ticket_is_cancelled_without_changing_its_history(self):
        ticket = self.ticket(state='pending', status='closed')
        step = TicketStep.objects.create(ticket=ticket, level=1, state='pending', status='active')
        TicketAssignee.objects.create(step=step, assignee=self.alice)
        updated_at = timezone.now() - timedelta(days=30)
        Ticket.objects.filter(pk=ticket.pk).update(date_updated=updated_at)
        with patch('tickets.workflow.business.apply_approved_effect') as effect:
            self.assertEqual(self.import_ticket(ticket), [])
        effect.assert_not_called()
        ticket.refresh_from_db()
        instance = WorkflowInstance.objects.get(ticket=ticket)
        self.assertEqual((ticket.state, ticket.status), ('closed', 'closed'))
        self.assertEqual(ticket.date_updated, updated_at)
        self.assertEqual((instance.state, instance.date_finished), ('cancelled', updated_at))
        self.assertEqual((instance.context['legacy']['state'], instance.context['legacy']['status']),
                         ('pending', 'closed'))
        self.assertEqual(ApprovalTask.objects.get(node_instance__instance=instance).state, 'cancelled')
        self.assertFalse(instance.events.filter(type='action.executed').exists())
        self.assertFalse(Ticket.objects.filter(pk=ticket.pk, state='pending').exists())

    def test_bad_definition_rolls_back_all_partial_ticket_records(self):
        ticket = self.ticket()
        for _ in range(2):
            step = TicketStep.objects.create(ticket=ticket, level=1, state='pending')
            TicketAssignee.objects.create(step=step, assignee=self.alice)
        with self.assertRaises(ValueError):
            self.import_ticket(ticket)
        self.assertFalse(Workflow.objects.filter(name=f'Legacy ticket {ticket.pk}').exists())
        self.assertFalse(WorkflowInstance.objects.filter(ticket=ticket).exists())
        ticket.refresh_from_db()
        self.assertIsNone(ticket.workflow_id)

    def test_missing_asset_in_multi_connection_request_is_not_ignored(self):
        asset = Asset.objects.create(name='Existing target', address='192.0.2.25', platform=self.platform)
        ticket = self.ticket(meta={'login_asset_connections': [
            {'asset_id': str(asset.pk), 'account': 'audit'}, {'asset_id': None, 'account': 'audit'},
        ]})
        ticket.type = 'login_asset_confirm'
        ticket.request_data = {'apply_login_asset': str(asset.pk)}
        ticket.save()
        step = TicketStep.objects.create(ticket=ticket, level=1, state='pending', status='active')
        TicketAssignee.objects.create(step=step, assignee=self.alice)
        self.assertTrue(self.import_ticket(ticket))
        self.assertEqual(WorkflowInstance.objects.get(ticket=ticket).state, 'error')

    def test_failed_payload_copy_cannot_leave_running_login_ticket(self):
        ticket = self.ticket()
        ticket.request_data = {}
        ticket.save(update_fields=['request_data'])
        step = TicketStep.objects.create(ticket=ticket, level=1, status='active')
        TicketAssignee.objects.create(step=step, assignee=self.alice)
        self.assertTrue(self.import_ticket(ticket))
        ticket.refresh_from_db()
        self.assertEqual((ticket.state, ticket.status), ('error', 'closed'))
