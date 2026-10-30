from unittest.mock import patch
from uuid import uuid4

from django.apps import apps
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from rbac.builtin import BuiltinRole
from rbac.models import Role, RoleBinding
from tickets.api.workflow import WorkflowViewSet
from tickets.models import ApprovalRule, ApprovalTask, Ticket, TicketFlow, Workflow
from tickets.plugins import get_ticket_plugin, ticket_plugins
from tickets.signal_handlers.workflow import initialize_approval_workflows
from tickets.tests import test_workflow as fixtures
from tickets.workflow.engine import WorkflowEngine
from tickets.workflow.errors import WorkflowConfigurationError
from tickets.workflow.initialization import ensure_default_workflows, initialize_workflows


class WorkflowInitializationTests(TestCase):
    setUpTestData = fixtures.WorkflowTests.__dict__['setUpTestData']
    setUp = fixtures.WorkflowTests.setUp

    def test_upgrade_initializes_published_options_for_every_visible_type_and_is_repeatable(self):
        initialize_approval_workflows(apps.get_app_config('tickets'), apps, 'default')
        with tmp_to_root_org():
            before = list(Workflow.objects.values_list('id', 'enabled', 'active_version_id'))
        for plugin in ticket_plugins.all(visible=True):
            request = APIRequestFactory().get('/', {'org_id': self.org.pk, 'type': plugin.type})
            force_authenticate(request, self.applicant)
            response = WorkflowViewSet.as_view({'get': 'options_list'}, **WorkflowViewSet.options_list.kwargs)(request)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(response.data, plugin.type)
            with tmp_to_root_org():
                workflow = Workflow.objects.get(pk=response.data[0]['id'])
            self.assertTrue(workflow.enabled)
            self.assertIsNotNone(workflow.active_version.published_at)
            config = workflow.active_version.nodes.get(type='approval').config
            self.assertEqual(config['strategy'], 'any')
            self.assertEqual(config['approvers'], {'type': 'role', 'value': [BuiltinRole.system_admin.id]})
        initialize_workflows()
        with tmp_to_root_org():
            self.assertEqual(list(Workflow.objects.values_list('id', 'enabled', 'active_version_id')), before)

    def test_default_workflow_resolves_current_system_admins_and_requires_one_vote(self):
        role, _ = Role.objects.get_or_create(id=BuiltinRole.system_admin.id,
                                             defaults={'name': 'SystemAdmin', 'scope': 'system'})
        RoleBinding.objects_raw.bulk_create([
            RoleBinding(user=user, role=role, scope='system') for user in (self.alice, self.bob)
        ])
        with tmp_to_root_org():
            workflow = Workflow.objects.get(org_id=Organization.ROOT_ID, type='apply_asset', is_system=False)
        ticket = Ticket.objects.create(type='apply_asset', title='Use initialized flow', applicant=self.applicant,
                                       org_id=self.org.pk)
        instance = WorkflowEngine().start(ticket, workflow, {})
        self.assertEqual(instance.state, 'running')
        tasks = ApprovalTask.objects.filter(node_instance__instance=instance)
        self.assertEqual(set(tasks.values_list('assignee_id', flat=True)), {self.alice.pk, self.bob.pk})
        self.assertEqual(tasks.first().node_instance.required, 1)

    def test_custom_legacy_levels_and_cc_are_imported_once_without_reenabling(self):
        flow = TicketFlow.objects.create(name='Existing custom flow', type='general', approval_level=2)
        for level, user in enumerate((self.alice, self.bob), 1):
            rule = ApprovalRule.objects.create(level=level, users={'type': 'ids', 'ids': [str(user.pk)]})
            flow.rules.add(rule)
        flow.cc_users.add(self.carol)
        initialize_workflows()
        workflow = Workflow.objects.get(legacy_flow_id=flow.pk)
        self.assertTrue(workflow.enabled)
        version = workflow.active_version
        self.assertEqual(version.nodes.get(type='cc').config['users'], [str(self.carol.pk)])
        self.assertEqual([node.config['approvers']['value'] for node in version.nodes.filter(type='approval').order_by('key')],
                         [[str(self.alice.pk)], [str(self.bob.pk)]])
        workflow.enabled = False
        workflow.save(update_fields=['enabled'])
        initialize_workflows()
        workflow.refresh_from_db()
        self.assertFalse(workflow.enabled)
        self.assertEqual(workflow.active_version_id, version.pk)
        self.assertEqual(workflow.versions.count(), 1)

    def test_local_configuration_is_not_bypassed_by_a_new_global_default(self):
        plugin = get_ticket_plugin('general')
        custom = Workflow.objects.create(type=plugin.type, name='Disabled custom flow')
        with patch.object(ticket_plugins, 'all', return_value=[plugin]):
            ensure_default_workflows()
            with tmp_to_root_org():
                self.assertFalse(Workflow.objects.filter(type=plugin.type, org_id=Organization.ROOT_ID).exists())
                self.assertEqual(Workflow.objects.filter(type=plugin.type, org_id=self.org.pk).get().pk, custom.pk)
                self.assertTrue(Workflow.objects.get(type=plugin.type, org_id=self.other_org.pk).enabled)
            new_org = Organization.objects.create(name=f'New organization {uuid4()}')
        with tmp_to_org(new_org):
            self.assertTrue(Workflow.objects.get(type=plugin.type).enabled)

    def test_invalid_legacy_rule_is_not_replaced_with_a_weaker_default(self):
        flow = TicketFlow.objects.create(type='general', name='Missing reviewers')
        flow.rules.add(ApprovalRule.objects.create(users={'type': 'ids', 'ids': []}))
        with patch.object(ticket_plugins, 'all', return_value=[get_ticket_plugin('general')]), \
                self.assertLogs('tickets.workflow.initialization', level='WARNING'):
            initialize_workflows()
        placeholder = Workflow.objects.get(type='general', legacy_flow_id=flow.pk)
        self.assertFalse(placeholder.enabled)
        self.assertIsNone(placeholder.active_version_id)
        self.assertTrue(placeholder.migration_notes['requires_review'])

    def test_invalid_local_legacy_flow_cannot_fall_back_to_same_named_global_flow(self):
        with tmp_to_root_org():
            inherited = Workflow.objects.get(org_id=Organization.ROOT_ID, type='apply_asset', is_system=False)
        flow = TicketFlow.objects.create(type='apply_asset', name=inherited.name)
        flow.rules.add(ApprovalRule.objects.create(users={'type': 'ids', 'ids': []}))
        with self.assertLogs('tickets.workflow.initialization', level='WARNING'):
            initialize_workflows()
        self.assertFalse(Workflow.get_org_related_flows(self.org.pk).filter(pk=inherited.pk).exists())
        ticket = Ticket.objects.create(type='apply_asset', title='Do not bypass local rule',
                                       applicant=self.applicant, org_id=self.org.pk)
        with self.assertRaises(WorkflowConfigurationError):
            WorkflowEngine().start(ticket, inherited, {})

    def test_complex_legacy_selector_is_not_silently_enabled_as_fixed_users(self):
        selector = {'type': 'attrs', 'attrs': [{'name': 'username', 'match': 'exact', 'value': self.alice.username}]}
        flow = TicketFlow.objects.create(type='general', name='Complex custom rule')
        flow.rules.add(ApprovalRule.objects.create(users=selector))
        with self.assertLogs('tickets.workflow.initialization', level='WARNING'):
            initialize_workflows()
        workflow = Workflow.objects.get(legacy_flow_id=flow.pk)
        self.assertFalse(workflow.enabled)
        self.assertTrue(workflow.migration_notes['requires_review'])
        self.assertEqual(workflow.migration_notes['rules'][0]['legacy_selector'], selector)

    def test_local_flow_overrides_only_same_named_global_flow(self):
        with tmp_to_root_org():
            inherited = Workflow.objects.create(org_id=Organization.ROOT_ID, type='general', name='Same name')
            other = Workflow.objects.create(org_id=Organization.ROOT_ID, type='general', name='Other name')
        local = Workflow.objects.create(type='general', name='same NAME')
        choices = Workflow.get_org_related_flows(self.org.pk).filter(type='general')
        self.assertEqual(set(choices.values_list('pk', flat=True)), {local.pk, other.pk})
        self.assertIn(inherited.pk, Workflow.get_org_related_flows(self.other_org.pk).values_list('pk', flat=True))
