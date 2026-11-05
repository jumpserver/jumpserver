from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import get_commands
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase

from tickets.models import Ticket, TicketStep, TicketAssignee, Workflow, WorkflowInstance
from tickets.tests.test_workflow import WorkflowTests


class TicketUpgradeTests(TestCase):
    setUpTestData = WorkflowTests.__dict__['setUpTestData']
    setUp = WorkflowTests.setUp

    def test_failed_records_rollback_continue_and_log_only_bounded_summary(self):
        tickets = []
        for index in range(9):
            ticket = Ticket.objects.create(title=f'Upgrade {index}', type='general',
                                           applicant=self.applicant, org_id=self.org.pk)
            step = TicketStep.objects.create(ticket=ticket, status='active')
            TicketAssignee.objects.create(step=step, assignee=self.alice)
            tickets.append(ticket)
        broken = {ticket.pk for ticket in tickets[:-1]}
        migration = import_module('tickets.migrations.0010_ticket_workflow_refactor')
        state = MigrationLoader(connection).project_state([('tickets', '0010_ticket_workflow_refactor')])
        convert = migration.import_ticket

        def fail_after_writes(apps, db, ticket):
            warnings = convert(apps, db, ticket)
            if ticket.pk in broken:
                # Real DB violation after the instance/tasks exist, exercising savepoint rollback.
                Model = apps.get_model('tickets', 'Workflow')
                Model.objects.using(db).create(name=f'Legacy ticket {ticket.pk}', type=ticket.type,
                                               org_id=ticket.org_id)
            return warnings

        with patch.object(migration, 'import_ticket', fail_after_writes), self.assertLogs(
                'tickets.migrations.0010_ticket_workflow_refactor', level='WARNING') as logs:
            migration.migrate_legacy_tickets(state.apps, SimpleNamespace(connection=connection))
        self.assertEqual(len(logs.output), 1)
        self.assertIn('8 failed', logs.output[0])
        self.assertIn('first 5', logs.output[0])
        self.assertLess(len(logs.output[0]), 1600)
        self.assertFalse(WorkflowInstance.objects.filter(ticket_id__in=broken).exists())
        self.assertFalse(Workflow.objects.filter(name__in=[f'Legacy ticket {pk}' for pk in broken]).exists())
        self.assertFalse(Ticket.objects.filter(pk__in=broken, workflow__isnull=False).exists())
        good = WorkflowInstance.objects.get(ticket=tickets[-1])
        self.assertEqual(good.state, 'running')
        migration.migrate_legacy_tickets(state.apps, SimpleNamespace(connection=connection))
        self.assertEqual(WorkflowInstance.objects.filter(ticket__in=tickets).count(), 9)
        self.assertEqual(WorkflowInstance.objects.get(ticket=tickets[-1]).pk, good.pk)

    def test_failure_sample_is_not_hidden_by_earlier_warnings(self):
        migration = import_module('tickets.migrations.0010_ticket_workflow_refactor')
        rows = [SimpleNamespace(pk=f'warning-{index}', org_id=self.org.pk) for index in range(6)]
        rows.append(SimpleNamespace(pk='failed-ticket', org_id=self.org.pk))

        def convert(row):
            if row.pk == 'failed-ticket':
                raise ValueError('Invalid legacy approval graph')
            return ['Legacy resources need review']

        with self.assertLogs('tickets.migrations.0010_ticket_workflow_refactor', level='WARNING') as logs:
            migration.migrate_rows(rows, convert, connection.alias, 'instances')
        self.assertEqual(len(logs.output), 1)
        self.assertIn('1 failed, 6 require review; first 5:', logs.output[0])
        self.assertIn('id=failed-ticket', logs.output[0])
        self.assertIn('Invalid legacy approval graph', logs.output[0])
        self.assertLess(logs.output[0].index('id=failed-ticket'), logs.output[0].index('id=warning-0'))
        self.assertEqual(logs.output[0].count('id='), 5)
        self.assertNotIn('id=warning-4', logs.output[0])

    def test_manual_instance_migration_command_is_removed(self):
        self.assertNotIn('migrate_ticket_instances', get_commands())
