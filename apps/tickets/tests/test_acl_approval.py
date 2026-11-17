from types import SimpleNamespace

from django.core.cache import cache
from django.db import transaction
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from assets.models import Asset, Platform
from acls.models import LoginACL, LoginAssetACL, CommandFilterACL
from acls.serializers.login_acl import LoginACLSerializer
from acls.serializers.login_asset_acl import LoginAssetACLSerializer
from acls.serializers.command_acl import CommandFilterACLSerializer
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from rbac.builtin import BuiltinRole
from rbac.models import Role, RoleBinding
from tickets.api.workflow import WorkflowViewSet
from terminal.models import Session
from tickets.models import Ticket, Workflow, WorkflowInstance, ApprovalTask
from tickets.workflow.errors import WorkflowConfigurationError
from authentication.services.connection_acl import get_review_group_key
from tickets.serializers.ticket.ticket import TicketApplySerializer
from tickets.serializers.workflow import WorkflowInstanceDetailSerializer
from tickets.tests import test_workflow as fixtures
from tickets.workflow.engine import WorkflowEngine
from tickets.workflow.context import snapshot_assets
from tickets.workflow.business import get_system_workflow
from tickets.workflow.publication import publish_workflow
from users.models import User


@override_settings(XPACK_LICENSE_IS_VALID=True)
class ACLApprovalTests(TestCase):
    org: Organization
    other_org: Organization
    applicant: User
    alice: User
    bob: User
    carol: User
    outsider: User
    platform: Platform
    factory: APIRequestFactory
    engine: WorkflowEngine

    setUpTestData = fixtures.WorkflowTests.__dict__['setUpTestData']
    setUp = fixtures.WorkflowTests.setUp
    cases = (
        (LoginACL, LoginACLSerializer, 'login_confirm'),
        (LoginAssetACL, LoginAssetACLSerializer, 'login_asset_confirm'),
        (CommandFilterACL, CommandFilterACLSerializer, 'command_confirm'),
    )

    def test_existing_acl_modes_and_pending_tasks_survive_mode_changes(self):
        asset = Asset.objects.create(
            name='Review asset', address='192.0.2.10', platform=self.platform,
        )
        for model, serializer_class, ticket_type in self.cases:
            org = Organization.root() if model is LoginACL else self.org
            with self.subTest(model=model.__name__), tmp_to_org(org):
                acl = model.objects.create(
                    name='Existing ACL', **({'action': 'accept', 'review_enabled': True}
                                           if model is LoginAssetACL else {'action': 'review'}),
                )
                acl.reviewers.set([self.alice, self.bob])
                self.assertIsNone(serializer_class(acl).data['workflow'])
                internal = get_system_workflow(str(org.pk), ticket_type, acl.reviewers.all())
                self.assertEqual(internal.pk, get_system_workflow(
                    str(org.pk), ticket_type, acl.reviewers.all(),
                ).pk)
                ticket = Ticket.objects.create(
                    type=ticket_type, title='Existing approval', applicant=self.applicant,
                    org_id=org.pk, workflow=internal,
                )
                instance = self.engine.start(ticket, internal, {
                    'assets': (snapshot_assets([asset], self.org.pk)
                               if model is not LoginACL else []),
                    'accounts': [{'username': 'root'}],
                })
                tasks = list(ApprovalTask.objects.filter(
                    node_instance__instance=instance,
                ).values_list('pk', 'assignee_id', 'state'))
                workflow = Workflow.objects.create(
                    name='Configured approval', type=ticket_type, org_id=org.pk,
                )
                publish_workflow(workflow, fixtures.approval_definition([self.carol]))
                workflow.refresh_from_db()
                workflow.enabled = True
                workflow.save(update_fields=['enabled'])
                serializer = serializer_class(
                    acl, data={'workflow': str(workflow.pk)}, partial=True,
                )
                self.assertTrue(serializer.is_valid(), serializer.errors)
                serializer.save()
                self.assertEqual(serializer_class(acl).data['workflow'], str(workflow.pk))
                self.assertCountEqual(acl.reviewers.all(), [self.alice, self.bob])
                serializer = serializer_class(acl, data={'workflow': None}, partial=True)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                serializer.save()
                self.assertIsNone(acl.workflow_id)
                instance.refresh_from_db()
                self.assertEqual(instance.version_id, internal.active_version_id)
                self.assertEqual(list(ApprovalTask.objects.filter(
                    node_instance__instance=instance,
                ).values_list('pk', 'assignee_id', 'state')), tasks)
                self.assertTrue(
                    WorkflowInstanceDetailSerializer(instance).data['workflow_is_system'],
                )
                task = ApprovalTask.objects.get(
                    node_instance__instance=instance, assignee=self.alice,
                )
                self.engine.approve(task, self.alice)
                instance.refresh_from_db()
                self.assertEqual(instance.state, 'approved')

    def test_clearing_workflow_requires_available_reviewers(self):
        User.objects.filter(pk=self.bob.pk).update(is_active=False)
        for model, serializer_class, ticket_type in self.cases:
            org = Organization.root() if model is LoginACL else self.org
            with self.subTest(model=model.__name__), tmp_to_org(org):
                workflow = Workflow.objects.create(
                    name='Bound flow', type=ticket_type, org_id=org.pk,
                )
                acl = model.objects.create(
                    name='Workflow ACL', workflow=workflow,
                    **({'action': 'accept', 'review_enabled': True}
                       if model is LoginAssetACL else {'action': 'review'}),
                )
                reviewers = [[], [str(self.bob.pk)]]
                if model is not LoginACL:
                    reviewers.append([str(self.outsider.pk)])
                for users in reviewers:
                    serializer = serializer_class(
                        acl, data={'workflow': None, 'reviewers': users}, partial=True,
                    )
                    self.assertFalse(serializer.is_valid())
                    self.assertIn('reviewers', serializer.errors)

    def test_internal_workflows_cannot_be_bound_by_public_serializers(self):
        for model, serializer_class, ticket_type in self.cases:
            org_id = Organization.ROOT_ID if model is LoginACL else str(self.org.pk)
            workflow = get_system_workflow(org_id, ticket_type, [self.alice])
            serializer = serializer_class(data={'workflow': str(workflow.pk)}, partial=True)
            self.assertFalse(serializer.is_valid())
            self.assertIn('workflow', serializer.errors)
        internal = get_system_workflow(str(self.org.pk), 'general', [self.alice])
        serializer = TicketApplySerializer(
            context={'request': SimpleNamespace(user=self.applicant)},
        )
        with self.assertRaises(ValidationError) as error:
            serializer.validate({
                'org_id': str(self.org.pk), 'type': 'general', 'workflow_id': internal.pk,
            })
        self.assertIn('workflow_id', error.exception.detail)

    def request(self, action, workflow=None, data=None, method='get'):
        request = getattr(self.factory, method)('/', data or {}, format='json')
        force_authenticate(request, self.alice)
        kwargs = getattr(getattr(WorkflowViewSet, action), 'kwargs', {})
        with transaction.atomic():
            return WorkflowViewSet.as_view({method: action}, **kwargs)(
                request, **({'pk': str(workflow.pk)} if workflow else {}),
            )

    def test_real_org_admin_permissions_and_internal_workflow_boundaries(self):
        role, _ = Role.objects.get_or_create(
            id=BuiltinRole.org_admin.id,
            defaults={'name': 'OrgAdmin', 'scope': 'org', 'builtin': True},
        )
        RoleBinding.objects_raw.create(user=self.alice, role=role, org=self.org, scope='org')
        self.alice.expire_rbac_perms_cache()
        response = self.request(
            'create', data={'name': 'Local approval', 'type': 'command_confirm'}, method='post',
        )
        self.assertEqual(response.status_code, 201, response.data)
        workflow = Workflow.objects.get(pk=response.data['id'])
        self.assertEqual(workflow.org_id, self.org.pk)
        response = self.request('publish', workflow, {
            'expected_version': 0, 'definition': fixtures.approval_definition([self.bob]),
        }, method='post')
        self.assertEqual(response.status_code, 201, response.data)
        response = self.request('partial_update', workflow, {'enabled': True}, method='patch')
        self.assertEqual(response.status_code, 200, response.data)
        internal = get_system_workflow(str(self.org.pk), 'command_confirm', [self.alice])
        self.assertNotIn(
            str(internal.pk), [item['id'] for item in self.request('list').data['results']],
        )
        self.assertNotIn(str(internal.pk), [item['id'] for item in self.request(
            'options_list', data={'org_id': str(self.org.pk), 'type': 'command_confirm'},
        ).data])
        for action, method in [('retrieve', 'get'), ('versions', 'get'),
                               ('partial_update', 'patch'), ('publish', 'post')]:
            self.assertEqual(self.request(action, internal, method=method).status_code, 404)
        with tmp_to_org(self.other_org):
            other = Workflow.objects.create(name='Other org', type='command_confirm')
        response = self.request('partial_update', other, {'enabled': False}, method='patch')
        self.assertEqual(response.status_code, 404)
        data = {'name': 'Global login', 'type': 'login_confirm'}
        response = self.request('create', data=data, method='post')
        self.assertEqual(response.status_code, 400, response.data)
        response = self.request('options_list', data={
            'org_id': Organization.ROOT_ID, 'type': 'login_confirm',
        })
        self.assertEqual(response.status_code, 403, response.data)
        with tmp_to_root_org():
            response = self.request('create', data=data, method='post')
            self.assertEqual(response.status_code, 403, response.data)


@override_settings(XPACK_LICENSE_IS_VALID=True)
class ACLReviewerSourceTests(TestCase):
    org: Organization
    other_org: Organization
    applicant: User
    alice: User
    bob: User
    carol: User
    outsider: User
    platform: Platform
    factory: APIRequestFactory
    engine: WorkflowEngine

    setUpTestData = fixtures.WorkflowTests.__dict__['setUpTestData']
    setUp = fixtures.WorkflowTests.setUp
    cases = ACLApprovalTests.cases

    def workflow(self, ticket_type, *, levels=1):
        org = Organization.root() if ticket_type == 'login_confirm' else self.org
        flow = Workflow.objects.create(name='ACL reviewer flow', type=ticket_type, org_id=org.pk)
        publish_workflow(flow, fixtures.approval_definition(
            [], levels=levels, approvers={'type': 'acl_reviewers'},
        ))
        flow.refresh_from_db()
        flow.enabled = True
        flow.save(update_fields=['enabled'])
        return flow

    def acl(self, model, flow, name='ACL', reviewers=None):
        acl = model.objects.create(
            name=name, workflow=flow,
            **({'action': 'accept', 'review_enabled': True, 'review_duration': 1}
               if model is LoginAssetACL else {'action': 'review'}),
        )
        acl.reviewers.set(reviewers if reviewers is not None else [self.alice])
        return acl

    def test_source_is_limited_to_acl_ticket_types(self):
        for ticket_type in ('general', 'apply_asset'):
            with self.subTest(ticket_type=ticket_type), transaction.atomic():
                with self.assertRaises(WorkflowConfigurationError):
                    self.workflow(ticket_type)

    def test_each_acl_requires_eligible_reviewers_for_the_published_source(self):
        User.objects.filter(pk=self.bob.pk).update(is_active=False)
        for model, serializer_class, ticket_type in self.cases:
            org = Organization.root() if model is LoginACL else self.org
            with self.subTest(ticket_type=ticket_type), tmp_to_org(org):
                flow = self.workflow(ticket_type)
                acl = self.acl(model, flow)
                self.assertTrue(serializer_class(acl).data['workflow_requires_reviewers'])
                invalid = [[], [str(self.bob.pk)]]
                if model is not LoginACL:
                    invalid.append([str(self.outsider.pk)])
                for reviewers in invalid:
                    serializer = serializer_class(acl, data={'reviewers': reviewers}, partial=True)
                    self.assertFalse(serializer.is_valid())
                    self.assertIn('reviewers', serializer.errors)
                serializer = serializer_class(
                    acl, data={'reviewers': [str(self.alice.pk)]}, partial=True,
                )
                self.assertTrue(serializer.is_valid(), serializer.errors)
                serializer.save()
                acl.reviewers.clear()
                serializer = serializer_class(
                    acl, data={'comment': 'Keep approval enabled'}, partial=True,
                )
                self.assertFalse(serializer.is_valid())
                self.assertIn('reviewers', serializer.errors)

    def test_login_and_command_entries_freeze_reviewers_and_workflow_version(self):
        for model, ticket_type in (
            (LoginACL, 'login_confirm'), (CommandFilterACL, 'command_confirm'),
        ):
            org = Organization.root() if model is LoginACL else self.org
            with self.subTest(ticket_type=ticket_type), tmp_to_org(org):
                flow = self.workflow(ticket_type, levels=2)
                acl = self.acl(model, flow)
                if model is LoginACL:
                    ticket = acl.create_confirm_ticket(None, self.applicant)
                else:
                    asset = Asset.objects.create(
                        name='Server', address='192.0.2.12', platform=self.platform,
                    )
                    session = Session.objects.create(
                        user=str(self.applicant), user_id=str(self.applicant.pk),
                        asset=asset.name, asset_id=str(asset.pk), account='root',
                    )
                    ticket = acl.create_command_review_ticket('whoami', session, acl, self.org.pk)
                instance = ticket.workflow_instance
                original_version = instance.version_id
                acl.reviewers.set([self.bob])
                publish_workflow(flow, fixtures.approval_definition([self.carol]))
                for _ in range(2):
                    task = ApprovalTask.objects.get(
                        node_instance__instance=instance, state='pending',
                    )
                    self.assertEqual(task.assignee_id, self.alice.pk)
                    self.engine.approve(task, self.alice)
                instance.refresh_from_db()
                self.assertEqual(instance.state, 'approved')
                self.assertEqual(instance.version_id, original_version)

    def test_same_flow_on_two_asset_acls_keeps_both_approvals_and_simple_approval(self):
        flow = self.workflow('login_asset_confirm')
        first = self.acl(LoginAssetACL, flow, 'A')
        second = self.acl(LoginAssetACL, flow, 'B', [self.bob])
        simple = self.acl(LoginAssetACL, None, 'C', [self.carol])
        asset = Asset.objects.create(name='Server', address='192.0.2.10', platform=self.platform)
        ticket = first.create_login_asset_review_ticket(
            self.applicant, asset, 'root', [], self.org.pk, review_acls=[first, second, simple],
        )
        instance = WorkflowInstance.objects.get(ticket=ticket)
        self.assertEqual(len(instance.context['acl_reviewers']), 2)
        second.reviewers.set([self.carol])
        for reviewer in (self.alice, self.bob, self.carol):
            task = ApprovalTask.objects.get(
                node_instance__instance=instance, state='pending',
            )
            self.assertEqual(task.assignee_id, reviewer.pk)
            self.engine.approve(task, reviewer)
        instance.refresh_from_db()
        self.assertEqual(instance.state, 'approved')

    def test_missing_or_forged_bindings_cannot_skip_approval(self):
        flow = self.workflow('command_confirm')
        ticket = Ticket.objects.create(
            type=flow.type, title='Untrusted binding', applicant=self.applicant,
        )
        with self.assertRaises(WorkflowConfigurationError):
            self.engine.start(ticket, flow, {'acl_reviewers': {'approval_0': [str(self.alice.pk)]}})
        with self.assertRaises(WorkflowConfigurationError):
            self.engine.start(
                ticket, flow, {}, acl_reviewers={'approval_0': [str(self.outsider.pk)]},
            )
        self.assertFalse(
            ApprovalTask.objects.filter(node_instance__instance__ticket=ticket).exists()
        )

    def test_asset_grouping_and_exemptions_include_acl_bound_reviewers(self):
        flow = self.workflow('login_asset_confirm')
        acl = self.acl(LoginAssetACL, flow)
        second = self.acl(LoginAssetACL, flow, 'Second', [self.bob])
        asset = Asset.objects.create(name='Server', address='192.0.2.11', platform=self.platform)
        key = acl.get_review_cache_key(self.applicant.pk, asset.pk, 'root')
        group = get_review_group_key(self.org.pk, [], [acl], self.applicant.pk)
        self.assertNotEqual(
            group, get_review_group_key(self.org.pk, [], [second], self.applicant.pk),
        )
        cache.set(key, 'original-approval', 60)
        self.addCleanup(cache.delete, key)
        self.assertTrue(acl.is_review_exempt(self.applicant, asset, 'root'))
        acl.reviewers.set([self.bob])
        self.assertFalse(acl.is_review_exempt(self.applicant, asset, 'root'))
        self.assertNotEqual(group, get_review_group_key(self.org.pk, [], [acl], self.applicant.pk))
        acl.reviewers.set([self.alice])
        publish_workflow(flow, fixtures.approval_definition(
            [], approvers={'type': 'acl_reviewers'}, levels=2,
        ))
        acl.refresh_from_db()
        self.assertFalse(acl.is_review_exempt(self.applicant, asset, 'root'))

    def test_multi_acl_cache_is_written_only_after_all_approvals(self):
        flow = self.workflow('login_asset_confirm')
        first = self.acl(LoginAssetACL, flow, 'A')
        second = self.acl(LoginAssetACL, flow, 'B', [self.bob])
        asset = Asset.objects.create(name='Server', address='192.0.2.13', platform=self.platform)
        for rule in (first, second):
            key = rule.get_review_cache_key(self.applicant.pk, asset.pk, 'root')
            cache.delete(key)
            self.addCleanup(cache.delete, key)
        ticket = first.create_login_asset_review_ticket(
            self.applicant, asset, 'root', [], self.org.pk, review_acls=[first, second],
        )
        instance = ticket.workflow_instance
        for reviewer in (self.alice, self.bob):
            task = ApprovalTask.objects.get(
                node_instance__instance=instance, state='pending',
            )
            with self.captureOnCommitCallbacks(execute=True):
                self.engine.approve(task, reviewer)
            for rule in (first, second):
                self.assertEqual(
                    rule.is_review_exempt(self.applicant, asset, 'root'), reviewer == self.bob,
                )
        second.reviewers.set([self.carol])
        self.assertTrue(first.is_review_exempt(self.applicant, asset, 'root'))
        self.assertFalse(second.is_review_exempt(self.applicant, asset, 'root'))

    def test_empty_acl_binding_cannot_borrow_another_rules_reviewers(self):
        flow = self.workflow('login_asset_confirm')
        first = self.acl(LoginAssetACL, flow, 'A')
        second = self.acl(LoginAssetACL, flow, 'B', [])
        asset = Asset.objects.create(name='Server', address='192.0.2.14', platform=self.platform)
        with self.assertRaises(WorkflowConfigurationError):
            first.create_login_asset_review_ticket(
                self.applicant, asset, 'root', [], self.org.pk, review_acls=[first, second],
            )
        self.assertFalse(Ticket.objects.exists())

    def test_workflow_options_describe_the_active_version(self):
        flow = self.workflow('command_confirm')
        request = self.factory.get(
            '/api/v1/tickets/workflows/options/', {'type': flow.type, 'org_id': str(self.org.pk)},
        )
        force_authenticate(request, self.alice)
        view = WorkflowViewSet.as_view(
            {'get': 'options_list'}, **WorkflowViewSet.options_list.kwargs,
        )
        response = view(request)
        self.assertEqual(response.status_code, 200)
        option = next(row for row in response.data if row['id'] == str(flow.pk))
        self.assertTrue(option['requires_acl_reviewers'])
        publish_workflow(flow, fixtures.approval_definition([self.alice]))
        response = view(request)
        option = next(row for row in response.data if row['id'] == str(flow.pk))
        self.assertFalse(option['requires_acl_reviewers'])
