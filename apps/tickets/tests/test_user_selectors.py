from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from django.utils.translation import override

from orgs.models import Organization
from orgs.utils import tmp_to_org
from rbac.models import Role, RoleBinding
from tickets.models import ApprovalRule, ApprovalTask, TicketFlow, Workflow
from tickets.tests import test_workflow as fixtures, test_workflow_upgrade as upgrade
from tickets.workflow.approvers import selected_users
from tickets.workflow.definition import validate_approvers
from tickets.workflow.errors import WorkflowConfigurationError
from tickets.workflow.engine import WorkflowEngine
from users.models import User, UserGroup


class UserSelectorValidationTests(SimpleTestCase):
    def test_invalid_filter_is_localized(self):
        with override('zh'), self.assertRaises(WorkflowConfigurationError) as error:
            validate_approvers({'type': 'user_selector', 'value': {}})
        self.assertEqual(str(error.exception.detail[0]), '用户筛选规则无效。')

    def test_filters_reject_unknown_fields_and_malformed_values(self):
        for selector in ({}, {'type': 'all', 'attrs': []}, {'type': 'ids', 'ids': []},
                         {'type': 'attrs', 'attrs': []}):
            with self.subTest(selector=selector), self.assertRaises(WorkflowConfigurationError):
                validate_approvers({'type': 'user_selector', 'value': selector})
        for attr in (
            {'name': 'password', 'value': '*'}, {'name': 'orgs__name', 'value': '*'},
            {'name': 'username', 'match': 'unknown', 'value': '*'},
            {'name': 'username', 'value': None}, {'name': 'is_active', 'value': 'false'},
            {'name': 'groups', 'match': 'm2m', 'value': ['invalid']},
            {'name': 'username', 'match': 'regex', 'value': '['},
        ):
            with self.subTest(attr=attr), self.assertRaises(WorkflowConfigurationError):
                validate_approvers({'type': 'user_selector', 'value': {'type': 'attrs', 'attrs': [attr]}})


class UserSelectorUpgradeTests(TestCase):
    engine: WorkflowEngine
    org: Organization
    other_org: Organization
    alice: User
    bob: User
    carol: User
    applicant: User
    outsider: User
    role: Role
    setUpTestData = fixtures.WorkflowTests.__dict__['setUpTestData']
    setUp = fixtures.WorkflowTests.setUp
    start = fixtures.WorkflowTests.start
    task = fixtures.WorkflowTests.task
    create_workflow = fixtures.WorkflowTests.create_workflow
    historical_import = upgrade.HistoricalWorkflowUpgradeTests.historical_import

    def upgraded_flow(self, selector):
        flow = TicketFlow.objects.create(name=str(uuid4()), type='general', approval_level=2)
        flow.rules.add(
            ApprovalRule.objects.create(level=1, users={'type': 'ids', 'ids': [str(self.alice.pk)]}),
            ApprovalRule.objects.create(level=2, users=selector),
        )
        self.assertEqual(self.historical_import(flow), [])
        workflow = Workflow.objects.get(legacy_flow_id=flow.pk)
        self.assertTrue(workflow.enabled)
        self.assertIsNotNone(workflow.active_version.published_at)
        self.assertEqual(workflow.active_version.nodes.get(key='approval_2').config['approvers'],
                         {'type': 'user_selector', 'value': selector})
        return workflow

    @patch('tickets.workflow.business.deliver_event')
    def test_upgraded_filters_are_dynamic_between_tickets_but_frozen_for_all_levels(self, _deliver):
        selector = {'type': 'attrs', 'attrs': [{'name': 'name', 'match': 'exact', 'value': 'bob', 'rel': 'and', 'index': 0}]}
        workflow = self.upgraded_flow(selector)
        instance = self.start(workflow)
        self.assertEqual(instance.context['approver_selections']['approval_2'], [str(self.bob.pk)])
        User.objects.filter(pk=self.bob.pk).update(name='Former reviewer')
        User.objects.filter(pk=self.carol.pk).update(name='bob')
        next_instance = self.start(workflow)
        self.assertEqual(next_instance.context['approver_selections']['approval_2'], [str(self.carol.pk)])
        self.engine.approve(self.task(instance, self.alice), self.alice)
        self.assertEqual(self.task(instance, self.bob).assignee_id, self.bob.pk)
        self.assertFalse(ApprovalTask.objects.filter(node_instance__instance=instance, assignee=self.carol).exists())
        self.engine.approve(self.task(instance, self.bob), self.bob)
        instance.refresh_from_db()
        self.assertEqual(instance.state, 'approved')

    def test_all_selector_and_no_current_matches_remain_valid_definitions(self):
        workflow = self.upgraded_flow({'type': 'all'})
        instance = self.start(workflow)
        self.assertNotIn(str(self.outsider.pk), instance.context['approver_selections']['approval_2'])
        workflow = self.upgraded_flow({'type': 'attrs', 'attrs': [{'name': 'name', 'value': 'not-yet-added'}]})
        with self.assertRaises(WorkflowConfigurationError):
            self.start(workflow)
        User.objects.filter(pk=self.bob.pk).update(name='not-yet-added')
        self.assertEqual(self.start(workflow).context['approver_selections']['approval_2'], [str(self.bob.pk)])

    def test_multiple_attribute_conditions_keep_roles_groups_and_exclusions(self):
        group_a = UserGroup.objects.create(name='A')
        group_b = UserGroup.objects.create(name='B')
        group_a.users.add(self.alice, self.bob)
        group_b.users.add(self.bob)
        selector = {'type': 'attrs', 'attrs': [
            {'name': 'groups', 'match': 'm2m_all', 'value': [str(group_a.pk), str(group_b.pk)]},
            {'name': 'org_roles', 'match': 'm2m', 'value': [str(self.role.pk)]},
            {'name': 'username', 'match': 'startswith', 'value': 'workflow-'},
            {'name': 'name', 'match': 'not', 'value': 'alice'},
        ]}
        workflow = self.upgraded_flow(selector)
        self.assertEqual(self.start(workflow).context['approver_selections']['approval_2'], [str(self.bob.pk)])

    def test_selector_rejects_foreign_references_and_excludes_unavailable_users(self):
        with tmp_to_org(self.other_org):
            group = UserGroup.objects.create(name='Foreign')
        with self.assertRaises(WorkflowConfigurationError):
            selected_users({'type': 'attrs', 'attrs': [
                {'name': 'groups', 'match': 'm2m', 'value': [str(group.pk)]},
            ]}, self.org.pk)
        User.objects.filter(pk=self.bob.pk).update(is_active=False)
        User.objects.filter(pk=self.carol.pk).update(date_expired=timezone.now() - timedelta(days=1))
        self.assertEqual(set(selected_users({'type': 'all'}, self.org.pk)), {self.applicant, self.alice})

    @patch('tickets.workflow.business.deliver_event')
    def test_frozen_later_approvers_are_still_checked_for_validity_and_organization(self, _deliver):
        for change in ('inactive', 'organization'):
            with self.subTest(change=change):
                workflow = self.upgraded_flow({'type': 'attrs', 'attrs': [{'name': 'name', 'value': 'bob'}]})
                instance = self.start(workflow)
                if change == 'inactive':
                    User.objects.filter(pk=self.bob.pk).update(is_active=False)
                else:
                    RoleBinding.objects_raw.filter(user=self.bob, org=self.org).delete()
                self.engine.approve(self.task(instance, self.alice), self.alice)
                instance.refresh_from_db()
                self.assertEqual(instance.state, 'error')
                self.assertFalse(ApprovalTask.objects.filter(node_instance__instance=instance, state='pending').exists())
                User.objects.filter(pk=self.bob.pk).update(is_active=True)
