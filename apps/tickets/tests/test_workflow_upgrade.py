from importlib import import_module
from uuid import uuid4

from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase

from orgs.utils import tmp_to_root_org
from tickets.models import ApprovalRule, Ticket, TicketFlow, Workflow
from assets.models import Asset
from tickets.tests import test_workflow as fixtures


migration = import_module('tickets.migrations.0010_ticket_workflow_refactor')
import_flow = migration.import_flow
default_workflows = migration.default_workflows
create_default = migration.create_default
SYSTEM_ADMIN_ID = migration.SYSTEM_ADMIN_ID


class HistoricalWorkflowUpgradeTests(TestCase):
    setUpTestData = fixtures.WorkflowTests.__dict__['setUpTestData']
    setUp = fixtures.WorkflowTests.setUp

    def historical_import(self, flow):
        apps = MigrationLoader(connection).project_state().apps
        old = apps.get_model('tickets', 'TicketFlow').objects.get(pk=flow.pk)
        return import_flow(apps, connection.alias, old)

    def test_historical_models_preserve_levels_cc_and_disabled_existing_workflow(self):
        flow = TicketFlow.objects.create(name='Historic approval', type='general')
        for level, user in enumerate([self.alice, self.bob], 1):
            flow.rules.add(ApprovalRule.objects.create(level=level, users={'type': 'ids', 'ids': [str(user.pk)]}))
        flow.cc_users.add(self.carol)
        self.assertEqual(self.historical_import(flow), [])
        workflow = Workflow.objects.get(legacy_flow_id=flow.pk)
        self.assertTrue(workflow.enabled)
        self.assertEqual(workflow.active_version.nodes.get(type='cc').config['users'], [str(self.carol.pk)])
        self.assertEqual(workflow.active_version.nodes.get(key='approval_2').config['approvers']['value'], [str(self.bob.pk)])
        workflow.enabled = False
        workflow.save(update_fields=['enabled'])
        self.historical_import(flow)
        workflow.refresh_from_db()
        self.assertFalse(workflow.enabled)
        self.assertEqual(workflow.versions.count(), 1)

    def test_missing_or_cross_org_user_disables_flow_without_dropping_other_approvers(self):
        for missing in [uuid4(), self.outsider.pk]:
            flow = TicketFlow.objects.create(name=str(missing), type='general')
            flow.rules.add(ApprovalRule.objects.create(users={'type': 'ids', 'ids': [str(self.alice.pk), str(missing)]}))
            self.assertTrue(self.historical_import(flow))
            workflow = Workflow.objects.get(legacy_flow_id=flow.pk)
            self.assertFalse(workflow.enabled)
            self.assertIsNone(workflow.active_version_id)

    def test_role_selector_remains_dynamic(self):
        flow = TicketFlow.objects.create(name='Role rule', type='general')
        flow.rules.add(ApprovalRule.objects.create(users={'type': 'attrs', 'attrs': [
            {'name': 'system_roles', 'match': 'm2m', 'value': [SYSTEM_ADMIN_ID]},
        ]}))
        self.assertEqual(self.historical_import(flow), [])
        workflow = Workflow.objects.get(legacy_flow_id=flow.pk)
        self.assertEqual(workflow.active_version.nodes.get(type='approval').config['approvers'],
                         {'type': 'role', 'value': [SYSTEM_ADMIN_ID]})

    def test_missing_role_disables_flow(self):
        flow = TicketFlow.objects.create(name='Missing role', type='general')
        flow.rules.add(ApprovalRule.objects.create(users={'type': 'attrs', 'attrs': [
            {'name': 'org_roles', 'match': 'm2m', 'value': [str(uuid4())]},
        ]}))
        self.assertTrue(self.historical_import(flow))
        workflow = Workflow.objects.get(legacy_flow_id=flow.pk)
        self.assertFalse(workflow.enabled)
        self.assertIsNone(workflow.active_version_id)

    def test_complex_selector_is_frozen_but_disabled(self):
        flow = TicketFlow.objects.create(name='Attribute rule', type='general')
        flow.rules.add(ApprovalRule.objects.create(users={'type': 'attrs', 'attrs': [
            {'name': 'username', 'match': 'exact', 'value': self.alice.username},
        ]}))
        self.assertTrue(self.historical_import(flow))
        workflow = Workflow.objects.get(legacy_flow_id=flow.pk)
        self.assertFalse(workflow.enabled)
        self.assertEqual(workflow.active_version.nodes.get(type='approval').config['approvers']['value'], [str(self.alice.pk)])

    def test_defaults_do_not_bypass_invalid_legacy_flow_or_duplicate(self):
        flow = TicketFlow.objects.create(name='Broken asset rule', type='apply_asset')
        flow.rules.add(ApprovalRule.objects.create(users={'type': 'ids', 'ids': []}))
        self.historical_import(flow)
        apps = MigrationLoader(connection).project_state().apps
        for _ in range(2):
            for candidate in default_workflows(apps, connection.alias):
                create_default(apps, connection.alias, *candidate)
        with tmp_to_root_org():
            own = Workflow.objects.filter(org_id=flow.org_id, type=flow.type, is_system=False)
            self.assertEqual(list(own.values_list('enabled', flat=True)), [False])
            for kind in ['change_secret', 'command_confirm', 'download_replay', 'file_transfer',
                         'login_asset_confirm', 'login_confirm', 'view_secret']:
                self.assertTrue(Workflow.objects.filter(type=kind, enabled=True, active_version__isnull=False).exists())


    def test_archived_child_keeps_ids_after_live_asset_and_user_deletion(self):
        with connection.cursor() as cursor:
            for table in ['tickets_applyassetticket', 'tickets_applyloginticket',
                          'tickets_applyloginassetticket', 'tickets_applycommandticket',
                          'tickets_applyassetticket_apply_assets', 'tickets_applyassetticket_apply_nodes']:
                constraints = connection.introspection.get_constraints(cursor, table)
                self.assertFalse(any(item['foreign_key'] for item in constraints.values()), table)
        asset = Asset.objects.create(name='Archive referenced host', address='192.0.2.250', platform=self.platform)
        ticket = Ticket.objects.create(title='Archive parent', type='login_asset_confirm', org_id=self.org.pk)
        prepare = lambda pk: Ticket._meta.pk.get_db_prep_value(pk, connection)
        ticket_id, asset_id, user_id = map(prepare, [ticket.pk, asset.pk, self.alice.pk])
        with connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO tickets_applyloginassetticket '
                '(ticket_ptr_id, apply_login_asset_id, apply_login_user_id, apply_login_account) VALUES (%s,%s,%s,%s)',
                [ticket_id, asset_id, user_id, 'archived-account'],
            )
        asset.delete()
        self.alice.delete()
        ticket.delete()
        connection.check_constraints()
        with connection.cursor() as cursor:
            cursor.execute('SELECT apply_login_asset_id, apply_login_user_id, apply_login_account '
                           'FROM tickets_applyloginassetticket WHERE ticket_ptr_id=%s', [ticket_id])
            row = cursor.fetchone()
        self.assertEqual(str(row[0]).replace('-', ''), str(asset_id).replace('-', ''))
        self.assertEqual(str(row[1]).replace('-', ''), str(user_id).replace('-', ''))
        self.assertEqual(row[2], 'archived-account')
