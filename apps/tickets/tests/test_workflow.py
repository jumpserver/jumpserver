from copy import deepcopy
from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import ValidationError as ModelValidationError
from django.core.management import call_command
from django.db import transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from django.utils.translation import override
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory, force_authenticate

from assets.models import Asset, Platform
from assets.serializers import AssetSerializer
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from rbac.builtin import BuiltinRole
from rbac.models import Permission, Role, RoleBinding
from tickets.api.workflow import WorkflowViewSet, WorkflowInstanceViewSet, ApprovalTaskViewSet
from tickets.models import (
    Ticket, TicketStep, TicketFlow, ApprovalRule, Workflow, WorkflowVersion,
    WorkflowNode, WorkflowInstance, WorkflowNodeInstance, ApprovalTask,
)
from tickets.workflow.conditions import evaluate_condition
from tickets.workflow.context import snapshot_assets
from tickets.workflow.definition import validate_definition
from tickets.workflow.engine import WorkflowEngine
from tickets.workflow.errors import WorkflowConfigurationError, WorkflowConflict
from tickets.workflow.publication import publish_workflow
from users.models import User, UserGroup


def approval_definition(users, *, levels=1, **config):
    nodes = [{'id': 'start', 'type': 'start'}]
    edges, previous = [], 'start'
    for index in range(levels):
        key = f'approval_{index}'
        nodes.append({'id': key, 'type': 'approval', 'config': {
            'approvers': {'type': 'user', 'value': [str(user.pk) for user in users]}, **deepcopy(config),
        }})
        edges.append([previous, key])
        previous = key
    nodes.append({'id': 'end', 'type': 'end'})
    edges.append([previous, 'end'])
    return {'nodes': nodes, 'edges': edges}


def conditional_definition(users):
    definition = approval_definition(users)
    definition['nodes'].insert(1, {'id': 'production', 'type': 'condition', 'config': {
        'field': 'asset.labels.env', 'operator': 'eq', 'value': 'prod',
    }})
    definition['edges'] = [['start', 'production'], ['production:true', 'approval_0'],
                           ['production:false', 'end'], ['approval_0', 'end']]
    return definition


class WorkflowDefinitionTests(SimpleTestCase):
    def setUp(self):
        self.definition = approval_definition([User(id=uuid4())])

    def test_normalizes_compact_edges_without_mutating_input(self):
        original = deepcopy(self.definition)
        normalized = validate_definition(self.definition)
        self.assertEqual(self.definition, original)
        self.assertEqual(normalized['edges'][0]['source'], 'start')
        self.assertTrue(normalized['nodes'][1]['config']['exclude_applicant'])

    def test_rejects_invalid_graphs_and_configs(self):
        cases = []
        for spec in [
            {'strategy': 'percentage'}, {'strategy': 'quorum', 'required': 0},
            {'strategy': 'quorum', 'required': True}, {'timeout_action': 'approve'},
            {'timeout': -1}, {'allow_transfer': 'true'}, {'approvers': {'type': []}},
            {'approvers': {'type': 'user', 'value': ['not-a-uuid']}}, {'script': 'print(1)'},
            {'approvers': {'type': 'applicant_manager'}},
        ]:
            definition = deepcopy(self.definition)
            definition['nodes'][1]['config'].update(spec)
            cases.append(definition)
        for edges in [
            [['start', 'absent']], [['start', 'approval_0'], ['approval_0', 'approval_0']],
            [['start', 'approval_0'], ['approval_0', 'end'], ['end', 'approval_0']],
            [['start', 'approval_0'], ['start', 'end'], ['approval_0', 'end']],
        ]:
            cases.append({**deepcopy(self.definition), 'edges': edges})
        duplicate = deepcopy(self.definition)
        duplicate['nodes'].append(duplicate['nodes'][1])
        cases.append(duplicate)
        for definition in cases:
            with self.subTest(definition=definition), self.assertRaises(WorkflowConfigurationError):
                validate_definition(definition)

    def test_approval_timeout_requires_whole_minutes(self):
        for seconds in (0, 60, 120, 31536000):
            definition = deepcopy(self.definition)
            definition['nodes'][1]['config']['timeout'] = seconds
            with self.subTest(seconds=seconds):
                self.assertEqual(validate_definition(definition)['nodes'][1]['config']['timeout'], seconds)
        for seconds in (1, 59, 61, -60, 31536060, 60.0, True, None):
            definition = deepcopy(self.definition)
            definition['nodes'][1]['config']['timeout'] = seconds
            with self.subTest(seconds=seconds), self.assertRaises(WorkflowConfigurationError):
                validate_definition(definition)

    def test_quorum_counts_unique_specified_users(self):
        user = User(id=uuid4())
        for users in ([user], [user, user]):
            with self.subTest(users=users), override('en'), self.assertRaisesMessage(
                    WorkflowConfigurationError, 'Select at least 2 approvers; currently 1 selected.'):
                validate_definition(approval_definition(users, strategy='quorum', required=2))
        definition = approval_definition([user], strategy='quorum', required=2)
        definition['nodes'][1]['config']['approvers']['value'] = str(user.pk)
        with self.assertRaises(WorkflowConfigurationError):
            validate_definition(definition)
        definition = validate_definition(approval_definition(
            [user, User(id=uuid4())], strategy='quorum', required=2,
        ))
        self.assertEqual(definition['nodes'][1]['config']['required'], 2)

    def test_quorum_does_not_count_dynamic_resolver_ids_as_users(self):
        for kind in ('user_group', 'role', 'org_admin', 'asset_owner'):
            approvers = {'type': kind}
            if kind in ('user_group', 'role'):
                approvers['value'] = [str(uuid4())]
            with self.subTest(kind=kind):
                definition = validate_definition(approval_definition(
                    [], approvers=approvers, strategy='quorum', required=2,
                ))
                self.assertEqual(definition['nodes'][1]['config']['required'], 2)

    def test_rejects_disconnected_cycle_and_missing_condition_branch(self):
        graph = deepcopy(self.definition)
        for key in ('a', 'b'):
            graph['nodes'].append({**deepcopy(graph['nodes'][1]), 'id': key})
        graph['edges'] += [['a', 'b'], ['b', 'a']]
        with self.assertRaises(WorkflowConfigurationError):
            validate_definition(graph)
        branch = conditional_definition([User(id=uuid4())])
        branch['edges'].pop(2)
        with self.assertRaises(WorkflowConfigurationError):
            validate_definition(branch)

    def test_cc_node_allows_empty_recipients_but_validates_user_ids(self):
        graph = deepcopy(self.definition)
        graph['nodes'].insert(1, {'id': 'cc', 'type': 'cc', 'config': {'users': [str(uuid4())]}})
        graph['edges'] = [['start', 'cc'], ['cc', 'approval_0'], ['approval_0', 'end']]
        self.assertEqual(validate_definition(graph)['nodes'][1]['type'], 'cc')
        graph['nodes'][1]['config']['users'] = []
        self.assertEqual(validate_definition(graph)['nodes'][1]['config'], {'users': []})
        for config in ({}, {'users': None}, {'users': str(uuid4())}, {'users': ['bad']},
                       {'users': [str(uuid4())] * 1001}, {'users': [str(uuid4())], 'script': 'x'}):
            invalid = deepcopy(graph)
            invalid['nodes'][1]['config'] = config
            with self.subTest(config=config), self.assertRaises(WorkflowConfigurationError):
                validate_definition(invalid)

    def test_conditions_use_domain_types_and_explicit_collection_semantics(self):
        context = {'assets': [{'labels': {'env': 'test'}}, {'labels': {'env': 'prod'}}],
                   'request': {'duration': 36000}, 'risk_level': 'critical', 'actions': ['connect']}
        self.assertTrue(evaluate_condition({'and': [
            {'field': 'asset.labels.env', 'operator': 'eq', 'value': 'prod'},
            {'field': 'request.duration', 'operator': 'gt', 'value': 28800},
            {'field': 'risk_level', 'operator': 'gte', 'value': 'high'},
        ]}, context))
        self.assertFalse(evaluate_condition({'field': 'asset.labels.env', 'operator': 'ne', 'value': 'prod'}, context))
        self.assertFalse(evaluate_condition({'field': 'asset.labels.env', 'operator': 'eq', 'value': 'prod', 'quantifier': 'all'}, context))
        self.assertTrue(evaluate_condition({'field': 'actions', 'operator': 'contains', 'value': 'connect'}, context))
        with self.assertRaises(WorkflowConfigurationError):
            evaluate_condition({'field': 'request.duration', 'operator': 'eq', 'value': True}, {'request': {'duration': 1}})

    def test_all_operators(self):
        cases = [('eq', 8, 8, True), ('ne', 8, 9, True), ('gt', 8, 9, False), ('gte', 8, 8, True),
                 ('lt', 8, 9, True), ('lte', 8, 8, True), ('in', 8, [8, 9], True),
                 ('not_in', 8, [1, 2], True), ('contains', 'prod-db', 'prod', True), ('exists', 8, True, True)]
        for operator, actual, expected, result in cases:
            with self.subTest(operator=operator):
                self.assertEqual(evaluate_condition({'field': 'duration', 'operator': operator, 'value': expected}, {'duration': actual}), result)

    def test_missing_or_wrongly_typed_context_never_silently_skips_approval(self):
        condition = {'field': 'request.duration', 'operator': 'gt', 'value': 8}
        for context in [{}, {'request': {'duration': '9'}}, {'request': {'duration': None}}]:
            with self.assertRaises(WorkflowConfigurationError):
                evaluate_condition(condition, context)
        self.assertTrue(evaluate_condition({'field': 'request.duration', 'operator': 'exists', 'value': False}, {}))


class WorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with tmp_to_root_org():
            cls.org = Organization(id=str(uuid4()), name='Workflow organization')
            cls.other_org = Organization(id=str(uuid4()), name='Other workflow organization')
            Organization.objects.bulk_create([cls.org, cls.other_org])
            cls.applicant, cls.alice, cls.bob, cls.carol, cls.outsider = [
                User(username=f'workflow-{name}', name=name, email=f'{name}@workflow.example.test')
                for name in ['applicant', 'alice', 'bob', 'carol', 'outsider']
            ]
            User.objects.bulk_create([cls.applicant, cls.alice, cls.bob, cls.carol, cls.outsider])
            cls.role = Role.objects.create(name='Workflow reviewers', scope='org')
            RoleBinding.objects_raw.bulk_create([
                RoleBinding(user=user, role=cls.role, org=org, scope='org')
                for org, users in [(cls.org, [cls.applicant, cls.alice, cls.bob, cls.carol]), (cls.other_org, [cls.outsider])]
                for user in users
            ])
            cls.platform = Platform.objects.create(name='Workflow test platform', category='host', type='linux')

    def setUp(self):
        context = tmp_to_org(self.org)
        context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)
        self.engine = WorkflowEngine()
        self.factory = APIRequestFactory()

    def create_workflow(self, definition=None, **config):
        workflow = Workflow.objects.create(name=f'Workflow {uuid4()}', type='general')
        publish_workflow(workflow, definition or approval_definition([self.alice, self.bob], **config))
        workflow.refresh_from_db()
        workflow.enabled = True
        workflow.save(update_fields=['enabled'])
        return workflow

    def start(self, workflow=None, context=None, **config):
        workflow = workflow or self.create_workflow(**config)
        ticket = Ticket.objects.create(title='Workflow ticket', applicant=self.applicant, org_id=self.org.id)
        return self.engine.start(ticket, workflow, context or {})

    def task(self, instance, user):
        return ApprovalTask.objects.get(node_instance__instance=instance, state='pending', assignee=user)

    def request(self, viewset, action, user, pk=None, data=None, method='post'):
        request = getattr(self.factory, method)('/api/v1/tickets/workflows/', data or {}, format='json')
        force_authenticate(request, user)
        # Match the request transaction boundary; DRF marks handled 4xx responses
        # for rollback when ATOMIC_REQUESTS is enabled (as in PostgreSQL config).
        with transaction.atomic(), patch.object(User, 'has_perm', return_value=False):
            return viewset.as_view({method: action})(request, **({'pk': str(pk)} if pk else {}))

    def test_any_approval_cancels_remaining_and_rejects_replay(self):
        instance = self.start()
        task = self.task(instance, self.alice)
        self.assertEqual(self.engine.approve(task, self.alice).state, 'approved')
        self.assertEqual(ApprovalTask.objects.filter(node_instance__instance=instance, state='cancelled').count(), 1)
        with self.assertRaises(WorkflowConflict):
            self.engine.approve(task, self.alice)
        self.assertEqual(instance.events.filter(type='workflow.completed').count(), 1)

    def test_all_and_quorum_wait_for_required_votes(self):
        for config in [{'strategy': 'all'}, {'strategy': 'quorum', 'required': 2}]:
            with self.subTest(config=config):
                instance = self.start(**config)
                self.assertEqual(self.engine.approve(self.task(instance, self.alice), self.alice).state, 'running')
                self.assertEqual(self.engine.approve(self.task(instance, self.bob), self.bob).state, 'approved')

    def test_any_rejection_terminates_entire_workflow(self):
        instance = self.start(strategy='all')
        self.engine.approve(self.task(instance, self.alice), self.alice)
        self.assertEqual(self.engine.reject(self.task(instance, self.bob), self.bob, 'No access').state, 'rejected')

    def test_more_than_five_levels(self):
        workflow = self.create_workflow(approval_definition([self.alice], levels=8))
        instance = self.start(workflow)
        for index in range(8):
            task = self.task(instance, self.alice)
            self.assertEqual(task.node_instance.node.key, f'approval_{index}')
            instance = self.engine.approve(task, self.alice)
        self.assertEqual(instance.state, 'approved')

    def test_branches_and_unvisited_nodes(self):
        workflow = self.create_workflow(conditional_definition([self.alice]))
        for environment, state in [('prod', 'running'), ('test', 'approved')]:
            instance = self.start(workflow, {'assets': [{'labels': {'env': environment}}]})
            self.assertEqual(instance.state, state)
            self.assertEqual(instance.events.get(type='condition.evaluated').data['result'], environment == 'prod')
            if environment == 'test':
                self.assertEqual(instance.node_instances.get(node__type='approval').state, 'skipped')

    def test_snapshot_and_bound_version_survive_later_changes(self):
        workflow = self.create_workflow(conditional_definition([self.alice]))
        context = {'assets': [{'labels': {'env': 'prod'}}]}
        instance = self.start(workflow, context)
        context['assets'][0]['labels']['env'] = 'test'
        old_version = instance.version_id
        publish_workflow(workflow, approval_definition([self.bob]), expected_version=1)
        instance.refresh_from_db()
        self.assertEqual(instance.context['assets'][0]['labels']['env'], 'prod')
        self.assertEqual(instance.version_id, old_version)
        self.assertEqual(self.engine.approve(self.task(instance, self.alice), self.alice).state, 'approved')
        self.assertEqual(self.start(workflow).version.number, 2)

    def test_context_is_immutable_through_save_and_bulk_update(self):
        instance = self.start()
        instance.context = {'risk_level': 'low'}
        with self.assertRaises(ModelValidationError):
            instance.save()
        with self.assertRaises(ModelValidationError):
            WorkflowInstance.objects.filter(pk=instance.pk).update(context={})

    def test_published_graph_rejects_all_regular_orm_mutations(self):
        workflow = self.create_workflow()
        version = workflow.active_version
        node = version.nodes.get(type='approval')
        node.name = 'Changed'
        operations = [
            lambda: node.save(), lambda: version.save(), lambda: version.delete(),
            lambda: version.nodes.update(name='Changed'), lambda: version.nodes.all().delete(),
            lambda: version.edges.all().delete(), lambda: version.nodes.bulk_update([node], ['name']),
            lambda: version.nodes.create(key='added', type='end'),
            lambda: WorkflowNode.objects.bulk_create([WorkflowNode(version=version, key='extra', type='end')]),
            lambda: WorkflowVersion.objects.filter(pk=version.pk).update(published_at=None),
        ]
        for operation in operations:
            with self.subTest(operation=operation), self.assertRaises(ModelValidationError):
                with transaction.atomic():
                    operation()
        self.assertEqual(version.nodes.count(), 3)

    def test_stale_publish_and_invalid_graph_are_atomic(self):
        workflow = self.create_workflow()
        with self.assertRaises(WorkflowConflict):
            publish_workflow(workflow, approval_definition([self.bob]), expected_version=0)
        with self.assertRaises(WorkflowConfigurationError):
            publish_workflow(workflow, {'nodes': [], 'edges': []}, expected_version=1)
        self.assertEqual(workflow.versions.count(), 1)

    def test_resolves_groups_and_roles_within_ticket_organization(self):
        group = UserGroup.objects.create(name='Reviewers')
        group.users.add(self.alice, self.outsider)
        for spec, expected in [
            ({'type': 'user_group', 'value': [str(group.pk)]}, {self.alice.pk}),
            ({'type': 'role', 'value': [str(self.role.pk)]}, {self.alice.pk, self.bob.pk, self.carol.pk}),
        ]:
            instance = self.start(approvers=spec)
            self.assertEqual(set(ApprovalTask.objects.filter(node_instance__instance=instance).values_list('assignee_id', flat=True)), expected)

    def test_missing_approvers_and_impossible_quorum_fail_closed_with_audit(self):
        for config in [
            {'approvers': {'type': 'user', 'value': [str(self.outsider.pk)]}},
            {'strategy': 'quorum', 'required': 2,
             'approvers': {'type': 'user', 'value': [str(self.alice.pk), str(self.applicant.pk)]}},
            {'approvers': {'type': 'asset_owner'}},
            {'approvers': {'type': 'org_admin'}},
            {'approvers': {'type': 'user', 'value': [str(self.applicant.pk)]}},
        ]:
            with self.subTest(config=config):
                instance = self.start(**config)
                self.assertEqual(instance.state, 'error')
                self.assertEqual(instance.events.filter(type='workflow.error').count(), 1)
                self.assertFalse(ApprovalTask.objects.filter(node_instance__instance=instance, state='pending').exists())

    def test_org_admin_resolves_ticket_organization_admins(self):
        admin, _ = Role.objects.get_or_create(id=BuiltinRole.org_admin.id,
                                              defaults={'name': 'OrgAdmin', 'scope': 'org'})
        RoleBinding.objects_raw.bulk_create([
            RoleBinding(user=user, role=admin, org=org, scope='org')
            for org, user in [(self.org, self.alice), (self.org, self.applicant),
                              (self.other_org, self.bob), (self.other_org, self.outsider)]
        ])
        workflow = self.create_workflow(approvers={'type': 'org_admin'})
        with tmp_to_root_org():
            instance = self.start(workflow)
        self.assertEqual(instance.state, 'running')
        self.assertEqual(set(ApprovalTask.objects.filter(node_instance__instance=instance)
                             .values_list('assignee_id', flat=True)), {self.alice.pk})

    def test_empty_approver_group_is_not_reported_as_an_exclusion(self):
        group = UserGroup.objects.create(name='Empty reviewers')
        with override('en'):
            instance = self.start(approvers={'type': 'user_group', 'value': [str(group.pk)]})
        self.assertEqual(instance.state, 'error')
        self.assertEqual(instance.events.get(type='workflow.error').data['detail'],
                         'An approval node must resolve between 1 and 1000 eligible approvers.')

    def test_excluded_approver_error_identifies_the_current_approval_level(self):
        definition = approval_definition([self.alice], levels=2)
        definition['nodes'][2]['config']['approvers']['value'] = [str(self.applicant.pk)]
        with override('en'):
            instance = self.start(self.create_workflow(definition))
            task = self.task(instance, self.alice)
            self.assertEqual(self.engine.approve(task, self.alice).state, 'error')
        self.assertEqual(instance.events.get(type='workflow.error').data['detail'],
                         'Approval 2 has no eligible approvers after excluding the applicant or authorized users. '
                         'Adjust the approvers or select another workflow.')
        task.refresh_from_db()
        self.assertEqual(task.state, 'approved')
        self.assertFalse(ApprovalTask.objects.filter(node_instance__instance=instance, state='pending').exists())

    def test_asset_owner_errors_identify_the_asset_and_fail_closed(self):
        cases = [
            ([], '资产“数据库”未配置负责人，请在资产编辑页面设置负责人。'),
            (['invalid-id'], '资产“数据库”的负责人信息无效，请在资产编辑页面重新设置负责人。'),
            ([str(self.outsider.pk)], '以下资产的负责人不可用（未启用、已过期、已删除或不属于当前组织）：数据库。请在资产编辑页面设置有效负责人。'),
        ]
        for owner_ids, expected in cases:
            with self.subTest(owner_ids=owner_ids), override('zh'):
                instance = self.start(context={'assets': [
                    {'name': '正常资产', 'owner_ids': [str(self.alice.pk)]},
                    {'name': '数据库', 'owner_ids': owner_ids},
                ]}, approvers={'type': 'asset_owner'})
                self.assertEqual(instance.state, 'error')
                self.assertEqual(instance.events.get(type='workflow.error').data['detail'], expected)
                self.assertFalse(ApprovalTask.objects.filter(node_instance__instance=instance).exists())

    def test_asset_owner_errors_report_inactive_expired_and_deleted_owners(self):
        for changes in ({'is_active': False}, {'date_expired': timezone.now() - timedelta(days=1)}, None):
            with self.subTest(changes=changes), transaction.atomic(), override('zh'):
                if changes is None:
                    User.objects.filter(pk=self.alice.pk).delete()
                else:
                    User.objects.filter(pk=self.alice.pk).update(**changes)
                instance = self.start(context={'assets': [
                    {'name': '数据库', 'owner_ids': [str(self.alice.pk)]},
                ]}, approvers={'type': 'asset_owner'})
                self.assertEqual(instance.state, 'error')
                self.assertIn('数据库', instance.events.get(type='workflow.error').data['detail'])
                self.assertFalse(ApprovalTask.objects.filter(node_instance__instance=instance).exists())
                transaction.set_rollback(True)

    def test_error_after_vote_preserves_vote_and_stops_progress(self):
        definition = approval_definition([self.alice], levels=2)
        definition['nodes'][2]['config']['approvers'] = {'type': 'asset_owner'}
        instance = self.start(self.create_workflow(definition))
        task = self.task(instance, self.alice)
        self.assertEqual(self.engine.approve(task, self.alice).state, 'error')
        task.refresh_from_db()
        self.assertEqual(task.state, 'approved')

    def test_missing_condition_context_is_an_error(self):
        instance = self.start(self.create_workflow(conditional_definition([self.alice])))
        self.assertEqual(instance.state, 'error')

    def test_duplicate_start_returns_same_instance_and_legacy_ticket_is_rejected(self):
        instance = self.start()
        second = self.engine.start(instance.ticket, instance.version.workflow, {})
        self.assertEqual(second.pk, instance.pk)
        self.assertEqual(instance.events.filter(type='workflow.started').count(), 1)
        ticket = Ticket.objects.create(title='Legacy', applicant=self.applicant, org_id=self.org.id)
        TicketStep.objects.create(ticket=ticket)
        with self.assertRaises(WorkflowConflict):
            self.engine.start(ticket, instance.version.workflow, {})

    def test_transfer_preserves_threshold_and_original_task_cannot_vote(self):
        instance = self.start(strategy='all', allow_transfer=True)
        original = self.task(instance, self.alice)
        self.engine.transfer(original, self.alice, self.carol, 'Please review')
        with self.assertRaises(WorkflowConflict):
            self.engine.approve(original, self.alice)
        self.assertEqual(self.engine.approve(self.task(instance, self.bob), self.bob).state, 'running')
        self.assertEqual(self.engine.approve(self.task(instance, self.carol), self.carol).state, 'approved')

    def test_added_approver_is_mandatory_and_does_not_replace_original_vote(self):
        for added_first in [True, False]:
            instance = self.start(allow_add_approver=True)
            self.engine.add_approver(self.task(instance, self.alice), self.alice, self.carol)
            first, last = (self.carol, self.alice) if added_first else (self.alice, self.carol)
            self.assertEqual(self.engine.approve(self.task(instance, first), first).state, 'running')
            self.assertEqual(self.engine.approve(self.task(instance, last), last).state, 'approved')

    def test_cannot_transfer_to_existing_applicant_or_foreign_user(self):
        instance = self.start(allow_transfer=True)
        for target in [self.bob, self.applicant, self.outsider]:
            with self.assertRaises(WorkflowConfigurationError):
                self.engine.transfer(self.task(instance, self.alice), self.alice, target)

    def test_disabled_transfer_and_addition(self):
        instance = self.start()
        for operation in (self.engine.transfer, self.engine.add_approver):
            with self.assertRaises(PermissionDenied):
                operation(self.task(instance, self.alice), self.alice, self.carol)

    def test_expiration_prevents_late_vote_and_is_idempotent(self):
        for action, expected in [('expire', 'expired'), ('reject', 'rejected')]:
            instance = self.start(timeout=60, timeout_action=action)
            task = self.task(instance, self.alice)
            WorkflowNodeInstance.objects.filter(pk=task.node_instance_id).update(deadline=timezone.now() - timedelta(seconds=1))
            self.assertEqual(self.engine.approve(task, self.alice).state, expected)
            self.assertEqual(self.engine.expire(instance).state, expected)
            self.assertEqual(instance.events.filter(type='approval.timed_out').count(), 1)
            self.assertEqual(ApprovalTask.objects.filter(node_instance__instance=instance, state='expired').count(), 2)

    def test_only_current_assignee_can_vote_and_only_applicant_can_cancel(self):
        instance = self.start()
        with self.assertRaises(PermissionDenied):
            self.engine.approve(self.task(instance, self.alice), self.bob)
        with self.assertRaises(PermissionDenied):
            self.engine.cancel(instance, self.alice)
        self.assertEqual(self.engine.cancel(instance, self.applicant).state, 'cancelled')

    def test_organization_isolation_for_engine_and_apis(self):
        instance = self.start()
        task = self.task(instance, self.alice)
        with tmp_to_org(self.other_org):
            with self.assertRaises(WorkflowInstance.DoesNotExist):
                self.engine.approve(task, self.alice)
            response = self.request(WorkflowInstanceViewSet, 'retrieve', self.applicant, instance.pk, method='get')
            self.assertEqual(response.status_code, 404)
            response = self.request(ApprovalTaskViewSet, 'approve', self.alice, task.pk)
            self.assertEqual(response.status_code, 404)

    def test_root_definition_resolves_approvers_in_instance_organization(self):
        with tmp_to_root_org():
            workflow = Workflow.objects.create(name='Global workflow', type='general', org_id=Organization.ROOT_ID)
            definition = approval_definition([], approvers={'type': 'role', 'value': [str(self.role.pk)]})
            publish_workflow(workflow, definition)
            Workflow.objects.filter(pk=workflow.pk).update(enabled=True)
        instance = self.start(workflow)
        self.assertFalse(ApprovalTask.objects.filter(node_instance__instance=instance, assignee=self.outsider).exists())

    def test_task_and_timeline_api_visibility_and_replay(self):
        instance = self.start()
        task = self.task(instance, self.alice)
        response = self.request(ApprovalTaskViewSet, 'list', self.alice, method='get')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([str(row['id']) for row in response.data['results']], [str(task.pk)])
        response = self.request(WorkflowInstanceViewSet, 'list', self.carol, method='get')
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(self.request(WorkflowInstanceViewSet, 'events', self.carol, instance.pk, method='get').status_code, 404)
        self.assertEqual(self.request(WorkflowInstanceViewSet, 'events', self.applicant, instance.pk, method='get').status_code, 200)
        self.assertEqual(self.request(ApprovalTaskViewSet, 'approve', self.bob, task.pk).status_code, 404)
        self.assertEqual(self.request(ApprovalTaskViewSet, 'approve', self.alice, task.pk).status_code, 200)
        self.assertEqual(self.request(ApprovalTaskViewSet, 'approve', self.alice, task.pk).status_code, 409)

    def test_instance_details_identify_the_used_workflow_version_and_role_sources(self):
        workflow = self.create_workflow(approvers={'type': 'role', 'value': [str(self.role.pk)]})
        instance = self.start(workflow)
        publish_workflow(workflow, approval_definition([], approvers={'type': 'org_admin'}), expected_version=1)
        response = self.request(WorkflowInstanceViewSet, 'retrieve', self.applicant, instance.pk, method='get')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['workflow_name'], workflow.name)
        self.assertEqual(response.data['version_number'], 1)
        self.assertEqual(response.data['approver_role_names'], {str(self.role.pk): self.role.name})
        approval = next(node for node in response.data['nodes'] if node['type'] == 'approval')
        self.assertEqual(approval['config']['approvers'], {'type': 'role', 'value': [str(self.role.pk)]})

    def test_instance_details_translate_builtin_roles_and_support_non_role_sources(self):
        admin = BuiltinRole.system_admin.get_role()
        RoleBinding.objects_raw.bulk_create([
            RoleBinding(user=self.alice, role=admin, scope='system'),
        ])
        workflow = self.create_workflow(approvers={'type': 'role', 'value': [str(admin.pk), str(self.role.pk)]})
        instance = self.start(workflow)
        with override('zh'):
            response = self.request(WorkflowInstanceViewSet, 'retrieve', self.applicant, instance.pk, method='get')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['approver_role_names'], {
            str(admin.pk): '系统管理员', str(self.role.pk): self.role.name,
        })
        instance = self.start()
        response = self.request(WorkflowInstanceViewSet, 'retrieve', self.applicant, instance.pk, method='get')
        self.assertEqual(response.data['approver_role_names'], {})

    def test_instance_preview_shows_remaining_levels_from_the_bound_version(self):
        definition = approval_definition([self.alice], levels=3)
        definition['nodes'][2]['config']['approvers'] = {'type': 'role', 'value': [str(self.role.pk)]}
        workflow = self.create_workflow(definition)
        instance = self.start(workflow)
        publish_workflow(workflow, approval_definition([self.bob]), expected_version=1)
        response = self.request(WorkflowInstanceViewSet, 'retrieve', self.applicant, instance.pk, method='get')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['version_number'], 1)
        self.assertEqual([(n['key'], n['state']) for n in response.data['upcoming_nodes']], [
            ('approval_1', 'not_started'), ('approval_2', 'not_started'), ('end', 'not_started'),
        ])
        self.assertEqual(response.data['approver_role_names'], {str(self.role.pk): self.role.name})
        self.assertEqual(instance.node_instances.count(), 2)
        self.assertEqual(ApprovalTask.objects.filter(node_instance__instance=instance).count(), 1)
        self.engine.approve(self.task(instance, self.alice), self.alice)
        response = self.request(WorkflowInstanceViewSet, 'retrieve', self.applicant, instance.pk, method='get')
        self.assertEqual([n['key'] for n in response.data['upcoming_nodes']], ['approval_2', 'end'])
        self.assertEqual([n['key'] for n in response.data['nodes']], ['start', 'approval_0', 'approval_1'])

    def test_instance_preview_distinguishes_undecided_branches_and_shared_successors(self):
        definition = approval_definition([self.alice], levels=4)
        definition['nodes'].insert(2, {'id': 'condition', 'type': 'condition', 'config': {
            'field': 'asset.labels.env', 'operator': 'eq', 'value': 'prod',
        }})
        definition['edges'] = [
            ['start', 'approval_0'], ['approval_0', 'condition'],
            ['condition:true', 'approval_1'], ['condition:false', 'approval_2'],
            ['approval_1', 'approval_3'], ['approval_2', 'approval_3'], ['approval_3', 'end'],
        ]
        instance = self.start(self.create_workflow(definition), {'assets': [{'labels': {'env': 'prod'}}]})
        response = self.request(WorkflowInstanceViewSet, 'retrieve', self.applicant, instance.pk, method='get')
        self.assertEqual({n['key']: n['state'] for n in response.data['upcoming_nodes']}, {
            'condition': 'not_started', 'approval_1': 'branch_pending', 'approval_2': 'branch_pending',
            'approval_3': 'not_started', 'end': 'not_started',
        })
        self.assertFalse(instance.events.filter(type='condition.evaluated').exists())
        self.engine.approve(self.task(instance, self.alice), self.alice)
        response = self.request(WorkflowInstanceViewSet, 'retrieve', self.applicant, instance.pk, method='get')
        self.assertEqual({n['key']: n['state'] for n in response.data['upcoming_nodes']}, {
            'approval_2': 'skipped', 'approval_3': 'not_started', 'end': 'not_started',
        })
        self.assertEqual(instance.node_instances.filter(node__key='approval_2').count(), 0)

    def test_instance_preview_stops_after_rejection_without_changing_skipped_records(self):
        instance = self.start(self.create_workflow(approval_definition([self.alice], levels=2)))
        self.engine.reject(self.task(instance, self.alice), self.alice)
        response = self.request(WorkflowInstanceViewSet, 'retrieve', self.applicant, instance.pk, method='get')
        self.assertEqual(response.data['upcoming_nodes'], [])
        self.assertEqual({n['key'] for n in response.data['nodes'] if n['state'] == 'skipped'}, {'approval_1', 'end'})

    def test_instance_preview_keeps_history_when_the_graph_is_restarted(self):
        instance = self.start(self.create_workflow(approval_definition([self.alice], levels=2)))
        self.engine.approve(self.task(instance, self.alice), self.alice)
        self.engine._close_pending(instance)
        instance.node_instances.filter(state='running').update(state='cancelled', date_finished=timezone.now())
        self.engine._execute(instance, instance.version.nodes.get(type='start'))
        response = self.request(WorkflowInstanceViewSet, 'retrieve', self.applicant, instance.pk, method='get')
        self.assertEqual([n['key'] for n in response.data['nodes']], [
            'start', 'approval_0', 'approval_1', 'start', 'approval_0',
        ])
        self.assertEqual([n['key'] for n in response.data['upcoming_nodes']], ['approval_1', 'end'])

    def test_empty_cc_nodes_publish_and_advance_without_recipients_or_notifications(self):
        from tickets.workflow.business import deliver_event

        definition = approval_definition([self.alice])
        definition['nodes'].extend([
            {'id': key, 'type': 'cc', 'config': {'users': []}}
            for key in ('cc_before', 'cc_after')
        ])
        definition['edges'] = [['start', 'cc_before'], ['cc_before', 'approval_0'],
                               ['approval_0', 'cc_after'], ['cc_after', 'end']]
        workflow = Workflow.objects.create(name='Optional CC', type='general')
        with patch.object(User, 'has_perms', return_value=True):
            response = self.request(WorkflowViewSet, 'publish', self.alice, workflow.pk, {
                'expected_version': 0, 'definition': definition,
            })
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual([node['config']['users'] for node in response.data['definition']['nodes']
                          if node['type'] == 'cc'], [[], []])
        workflow.refresh_from_db()
        workflow.enabled = True
        workflow.save(update_fields=['enabled'])
        instance = self.start(workflow)
        self.assertFalse(instance.ticket.cc_users.exists())
        self.assertEqual(self.task(instance, self.alice).node_instance.node.key, 'approval_0')
        with patch('tickets.notifications.TicketUpdatedToCcUserMessage') as notify:
            deliver_event(instance.events.get(type='cc.added').pk)
            notify.assert_not_called()
        self.assertEqual(self.engine.approve(self.task(instance, self.alice), self.alice).state, 'approved')
        self.assertFalse(instance.ticket.cc_users.exists())
        self.assertEqual(list(instance.events.filter(type='cc.added').values_list('data', flat=True)),
                         [{'recipients': [], 'added_recipients': []},
                          {'recipients': [], 'added_recipients': []}])

    def test_configured_cc_recipients_must_still_be_active_organization_members(self):
        definition = approval_definition([self.alice])
        definition['nodes'].insert(1, {'id': 'cc', 'type': 'cc', 'config': {'users': []}})
        definition['edges'] = [['start', 'cc'], ['cc', 'approval_0'], ['approval_0', 'end']]
        self.carol.is_active = False
        self.carol.save(update_fields=['is_active'])
        workflow = Workflow.objects.create(name='Validate CC recipients', type='general')
        for user in (self.outsider, self.carol):
            definition['nodes'][1]['config']['users'] = [str(user.pk)]
            with self.subTest(user=user.username), self.assertRaises(WorkflowConfigurationError):
                publish_workflow(workflow, definition)
        self.assertFalse(workflow.versions.exists())

    def test_publish_requires_permission_and_matching_version(self):
        workflow = self.create_workflow()
        data = {'expected_version': 0, 'definition': approval_definition([self.alice])}
        with patch.object(User, 'has_perms', return_value=False):
            self.assertEqual(self.request(WorkflowViewSet, 'publish', self.alice, workflow.pk, data).status_code, 403)
        with patch.object(User, 'has_perms', return_value=True):
            self.assertEqual(self.request(WorkflowViewSet, 'publish', self.alice, workflow.pk, data).status_code, 409)
            data['expected_version'] = 1
            self.assertEqual(self.request(WorkflowViewSet, 'publish', self.alice, workflow.pk, data).status_code, 201)

    def test_login_publication_rejects_org_admin_without_restricting_other_global_flows(self):
        definition = approval_definition([], approvers={'type': 'org_admin'})
        with tmp_to_root_org():
            workflow = Workflow.objects.create(name='Global login', type='login_confirm', org_id=Organization.ROOT_ID)
            with override('en'), patch.object(User, 'has_perms', return_value=True):
                response = self.request(WorkflowViewSet, 'publish', self.alice, workflow.pk, {
                    'expected_version': 0, 'definition': definition,
                })
            self.assertEqual(response.status_code, 400)
            self.assertIn('cannot use organization administrators', str(response.data))
            self.assertFalse(workflow.versions.exists())
            workflow.refresh_from_db()
            self.assertIsNone(workflow.active_version_id)
            other = Workflow.objects.create(name='Global assets', type='apply_asset', org_id=Organization.ROOT_ID)
            publish_workflow(other, definition)
            self.assertEqual(other.versions.count(), 1)

    def test_login_publication_rejects_asset_owners_without_restricting_asset_flows(self):
        definition = approval_definition([], approvers={'type': 'asset_owner'})
        with tmp_to_root_org(), override('en'), patch.object(User, 'has_perms', return_value=True):
            workflow = Workflow.objects.create(name='Login with asset owner', type='login_confirm',
                                               org_id=Organization.ROOT_ID)
            response = self.request(WorkflowViewSet, 'publish', self.alice, workflow.pk, {
                'expected_version': 0, 'definition': definition,
            })
        self.assertEqual(response.status_code, 400)
        self.assertIn('cannot use asset owners', str(response.data))
        self.assertFalse(workflow.versions.exists())
        workflow.refresh_from_db()
        self.assertIsNone(workflow.active_version_id)
        for ticket_type in ('apply_asset', 'login_asset_confirm'):
            with self.subTest(ticket_type=ticket_type):
                other = Workflow.objects.create(name=ticket_type, type=ticket_type)
                publish_workflow(other, definition)
                self.assertEqual(other.versions.count(), 1)

    def test_publish_rejects_impossible_quorum_without_creating_version(self):
        workflow = self.create_workflow()
        original_version = workflow.active_version_id
        for users in ([self.alice], [self.alice, self.alice]):
            data = {'expected_version': 1, 'definition': approval_definition(users, strategy='quorum', required=2)}
            with self.subTest(users=users), override('en'), patch.object(User, 'has_perms', return_value=True):
                response = self.request(WorkflowViewSet, 'publish', self.alice, workflow.pk, data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data, {
                    'definition': ['Select at least 2 approvers; currently 1 selected.'],
                })
        workflow.refresh_from_db()
        self.assertEqual(workflow.active_version_id, original_version)
        self.assertEqual(workflow.versions.count(), 1)

    def test_publish_unknown_condition_field_reports_full_path_without_creating_version(self):
        workflow = self.create_workflow()
        original_version = workflow.active_version_id
        for language, message in [('zh', '未知的流程上下文字段：{field}。'),
                                  ('zh-hant', '未知的流程上下文字段：{field}。'),
                                  ('en', 'Unknown workflow context field: {field}.')]:
            for field, nested in [('qa477_missing_field', False), ('qa477_missing_field.value', True)]:
                definition = conditional_definition([self.alice])
                condition = {'field': field, 'operator': 'eq', 'value': 'test'}
                definition['nodes'][1]['config'] = {'and': [condition]} if nested else condition
                data = {'expected_version': 1, 'definition': definition}
                with self.subTest(language=language, field=field), override(language), \
                        patch.object(User, 'has_perms', return_value=True):
                    response = self.request(WorkflowViewSet, 'publish', self.alice, workflow.pk, data)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.data, {'definition': [message.format(field=field)]})
        workflow.refresh_from_db()
        self.assertEqual(workflow.active_version_id, original_version)
        self.assertEqual(workflow.versions.count(), 1)

    def test_organization_workflow_permissions_do_not_expand_legacy_ticket_access(self):
        permissions = set(Permission.get_permissions('org').filter(
            content_type__app_label='tickets',
        ).values_list('codename', flat=True))
        self.assertEqual(permissions, {
            'add_workflow', 'change_workflow', 'view_workflow', 'view_workflowinstance',
            'apply_assetforothers',
        })

    def test_asset_owner_api_validation_and_snapshot_survive_owner_change(self):
        asset = Asset.objects.create(name='owned asset', address='127.0.0.1', platform=self.platform, owner=self.alice)
        serializer = AssetSerializer(asset, data={'owner': str(self.carol.pk)}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        invalid = AssetSerializer(asset, data={'owner': str(self.outsider.pk)}, partial=True)
        self.assertFalse(invalid.is_valid())
        self.assertIn('owner', invalid.errors)
        assets = snapshot_assets([asset], self.org.id)
        self.assertEqual(serializer.save().owner_id, self.carol.pk)
        Asset.objects.filter(pk=asset.pk).update(owner=self.bob)
        instance = self.start(context={'assets': assets}, approvers={'type': 'asset_owner'})
        self.assertEqual(self.task(instance, self.alice).assignee_snapshot['id'], str(self.alice.pk))
        self.assertEqual(instance.context['assets'][0]['owner']['username'], self.alice.username)
        serializer = AssetSerializer(asset, data={'owner': None}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.save().owner_id)

    def test_user_deletion_preserves_identity_in_audit_and_asset_owner_is_nullable(self):
        asset = Asset.objects.create(name='deleted owner', address='127.0.0.1', platform=self.platform, owner=self.alice)
        instance = self.start()
        task = self.task(instance, self.alice)
        self.engine.approve(task, self.alice)
        User.objects.filter(pk=self.alice.pk).delete()
        task.refresh_from_db()
        asset.refresh_from_db()
        self.assertIsNone(task.assignee_id)
        self.assertIsNone(asset.owner_id)
        self.assertEqual(task.assignee_snapshot['username'], 'workflow-alice')
        event = instance.events.get(type='approval.approved')
        self.assertIsNone(event.actor_id)
        self.assertEqual(event.actor_snapshot['username'], 'workflow-alice')

    def test_legacy_import_is_previewable_idempotent_and_disabled(self):
        flow = TicketFlow.objects.create(name='Legacy test flow', type='general')
        rule = ApprovalRule.objects.create(users={'type': 'ids', 'ids': [str(self.alice.pk)]})
        flow.rules.add(rule)
        output = StringIO()
        call_command('migrate_ticket_workflows', flow_id=str(flow.pk), stdout=output)
        self.assertFalse(Workflow.objects.filter(legacy_flow_id=flow.pk).exists())
        self.assertIn('WOULD IMPORT', output.getvalue())
        for _ in range(2):
            call_command('migrate_ticket_workflows', flow_id=str(flow.pk), apply=True, stdout=StringIO())
        workflow = Workflow.objects.get(legacy_flow_id=flow.pk)
        self.assertFalse(workflow.enabled)
        self.assertEqual(workflow.versions.count(), 1)
        self.assertTrue(workflow.migration_notes['requires_review'])
        self.assertTrue(TicketFlow.objects.filter(pk=flow.pk).exists())


class WorkflowCompositionTests(SimpleTestCase):
    def test_chain_preserves_condition_branches_and_configuration(self):
        from tickets.workflow.composition import chain_definitions
        user = User(id=uuid4())
        first = conditional_definition([user])
        second = approval_definition([user], strategy='quorum', required=1, timeout=600, timeout_action='reject')
        original = deepcopy([first, second])
        combined = chain_definitions([first, second])
        self.assertEqual([first, second], original)
        condition = next(node for node in combined['nodes'] if node['type'] == 'condition')
        next_approval = next(node for node in combined['nodes'] if node['config'].get('strategy') == 'quorum')
        false_edge = next(edge for edge in combined['edges']
                          if edge['source'] == condition['id'] and edge['condition'] is False)
        self.assertEqual(false_edge['target'], next_approval['id'])
        self.assertEqual(next_approval['config']['timeout_action'], 'reject')
        self.assertEqual(next_approval['config']['timeout'], 600)

    def test_chain_keeps_cc_and_accepts_empty_sections_without_extra_exits(self):
        from tickets.workflow.composition import chain_definitions
        user = User(id=uuid4())
        empty = {'nodes': [{'id': 's', 'type': 'start'}, {'id': 'e', 'type': 'end'}], 'edges': [['s', 'e']]}
        cc = {'nodes': [{'id': 's', 'type': 'start'}, {'id': 'cc', 'type': 'cc', 'config': {'users': [str(user.pk)]}},
                        {'id': 'e', 'type': 'end'}], 'edges': [['s', 'cc'], ['cc', 'e']]}
        combined = chain_definitions([empty, cc, empty, approval_definition([user]), empty])
        self.assertEqual([node['type'] for node in combined['nodes']], ['start', 'end', 'cc', 'approval'])
        self.assertEqual(len(combined['edges']), 3)

    def test_chain_rejects_total_size_over_limit(self):
        from tickets.workflow.composition import chain_definitions
        user = User(id=uuid4())
        with self.assertRaises(WorkflowConfigurationError):
            chain_definitions([approval_definition([user], levels=64), approval_definition([user], levels=64)])
