from datetime import timedelta
from importlib import import_module
from unittest.mock import patch

from django.db import connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase
from django.utils import timezone

from accounts.models import Account
from assets.models import Asset, Node
from orgs.utils import tmp_to_org
from perms.models import AssetPermission
from tickets.models import Ticket, TicketAssignee, TicketStep, Workflow, WorkflowInstance, ApprovalTask
from tickets.tests import test_workflow as fixtures
from tickets.workflow.engine import WorkflowEngine


import_ticket = import_module('tickets.migrations.0010_ticket_workflow_refactor').import_ticket


class HistoricalInstanceUpgradeTests(TestCase):
    setUpTestData = fixtures.WorkflowTests.__dict__['setUpTestData']

    def setUp(self):
        scope = tmp_to_org(self.org)
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.apps = MigrationLoader(connection).project_state().apps

    def import_ticket(self, ticket):
        historical = self.apps.get_model('tickets', 'Ticket').objects.get(pk=ticket.pk)
        with transaction.atomic():
            return import_ticket(self.apps, 'default', historical)

    def ticket(self, **kwargs):
        return Ticket.objects.create(type='login_confirm', title='Historical upgrade',
                                     applicant=self.applicant, org_id=self.org.pk,
                                     request_data={'apply_login_ip': '192.0.2.24'}, **kwargs)

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
        self.assertEqual(instance.context['request']['account_selectors'], ['audit'])
        self.assertEqual(instance.context['actions'], ['connect'])
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
        task = ApprovalTask.objects.get(node_instance__instance=instance, state='pending')
        with patch('tickets.workflow.business.deliver_event'):
            WorkflowEngine().approve(task, self.bob)
        permission = AssetPermission.objects.get(pk=ticket.pk)
        self.assertEqual(list(permission.assets.values_list('pk', flat=True)), [asset.pk])
        self.assertEqual(permission.accounts, ['audit'])
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
