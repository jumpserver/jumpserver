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
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory, force_authenticate

from assets.models import Asset, Platform
from assets.serializers import AssetSerializer
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
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
            {'strategy': 'quorum', 'required': 3},
            {'approvers': {'type': 'asset_owner'}},
            {'approvers': {'type': 'applicant_manager'}},
            {'approvers': {'type': 'user', 'value': [str(self.applicant.pk)]}},
        ]:
            with self.subTest(config=config):
                instance = self.start(**config)
                self.assertEqual(instance.state, 'error')
                self.assertEqual(instance.events.filter(type='workflow.error').count(), 1)
                self.assertFalse(ApprovalTask.objects.filter(node_instance__instance=instance, state='pending').exists())

    def test_snapshot_manager_resolver(self):
        instance = self.start(context={'applicant': {'manager_id': str(self.carol.pk)}}, approvers={'type': 'applicant_manager'})
        self.assertEqual(self.task(instance, self.carol).assignee_id, self.carol.pk)

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

    def test_publish_requires_permission_and_matching_version(self):
        workflow = self.create_workflow()
        data = {'expected_version': 0, 'definition': approval_definition([self.alice])}
        with patch.object(User, 'has_perms', return_value=False):
            self.assertEqual(self.request(WorkflowViewSet, 'publish', self.alice, workflow.pk, data).status_code, 403)
        with patch.object(User, 'has_perms', return_value=True):
            self.assertEqual(self.request(WorkflowViewSet, 'publish', self.alice, workflow.pk, data).status_code, 409)
            data['expected_version'] = 1
            self.assertEqual(self.request(WorkflowViewSet, 'publish', self.alice, workflow.pk, data).status_code, 201)

    def test_organization_workflow_permissions_do_not_expand_legacy_ticket_access(self):
        permissions = set(Permission.get_permissions('org').filter(
            content_type__app_label='tickets',
        ).values_list('codename', flat=True))
        self.assertEqual(permissions, {
            'add_workflow', 'change_workflow', 'view_workflow', 'view_workflowinstance',
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
