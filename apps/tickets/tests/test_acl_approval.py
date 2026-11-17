from types import SimpleNamespace

from django.db import transaction
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import force_authenticate

from assets.models import Asset
from acls.models import LoginACL, LoginAssetACL, CommandFilterACL
from acls.serializers.login_acl import LoginACLSerializer
from acls.serializers.login_asset_acl import LoginAssetACLSerializer
from acls.serializers.command_acl import CommandFilterACLSerializer
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from rbac.builtin import BuiltinRole
from rbac.models import Role, RoleBinding
from tickets.api.workflow import WorkflowViewSet
from tickets.models import Ticket, Workflow, ApprovalTask
from tickets.serializers.ticket.ticket import TicketApplySerializer
from tickets.serializers.workflow import WorkflowInstanceDetailSerializer
from tickets.tests import test_workflow as fixtures
from tickets.workflow.context import snapshot_assets
from tickets.workflow.business import get_system_workflow
from tickets.workflow.publication import publish_workflow


@override_settings(XPACK_LICENSE_IS_VALID=True)
class ACLApprovalTests(TestCase):
    setUpTestData = fixtures.WorkflowTests.__dict__['setUpTestData']
    setUp = fixtures.WorkflowTests.setUp
    cases = (
        (LoginACL, LoginACLSerializer, 'login_confirm'),
        (LoginAssetACL, LoginAssetACLSerializer, 'login_asset_confirm'),
        (CommandFilterACL, CommandFilterACLSerializer, 'command_confirm'),
    )

    def test_existing_acl_modes_and_pending_tasks_survive_mode_changes(self):
        asset = Asset.objects.create(name='Review asset', address='192.0.2.10', platform=self.platform)
        for model, serializer_class, ticket_type in self.cases:
            org = Organization.root() if model is LoginACL else self.org
            with self.subTest(model=model.__name__), tmp_to_org(org):
                kwargs = {'action': 'accept', 'review_enabled': True} if model is LoginAssetACL else {
                    'action': 'review',
                }
                acl = model.objects.create(name='Existing ACL', **kwargs)
                acl.reviewers.set([self.alice, self.bob])
                self.assertIsNone(serializer_class(acl).data['workflow'])
                internal = get_system_workflow(str(org.pk), ticket_type, acl.reviewers.all())
                self.assertEqual(internal.pk, get_system_workflow(
                    str(org.pk), ticket_type, acl.reviewers.all(),
                ).pk)
                ticket = Ticket.objects.create(type=ticket_type, title='Existing approval',
                                               applicant=self.applicant, org_id=org.pk, workflow=internal)
                instance = self.engine.start(ticket, internal, {
                    'assets': snapshot_assets([asset], self.org.pk) if model is not LoginACL else [],
                    'accounts': [{'username': 'root'}],
                })
                tasks = list(ApprovalTask.objects.filter(node_instance__instance=instance).values_list(
                    'pk', 'assignee_id', 'state',
                ))
                workflow = Workflow.objects.create(name='Configured approval', type=ticket_type, org_id=org.pk)
                publish_workflow(workflow, fixtures.approval_definition([self.carol]))
                workflow.refresh_from_db()
                workflow.enabled = True
                workflow.save(update_fields=['enabled'])
                serializer = serializer_class(acl, data={'workflow': str(workflow.pk)}, partial=True)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                serializer.save()
                self.assertEqual(serializer_class(acl).data['workflow'], str(workflow.pk))
                self.assertCountEqual(acl.reviewers.all(), [self.alice, self.bob])
                for reviewers in ([], [str(self.outsider.pk)] if org != Organization.root() else []):
                    invalid = serializer_class(acl, data={'workflow': None, 'reviewers': reviewers}, partial=True)
                    self.assertFalse(invalid.is_valid())
                    self.assertIn('reviewers', invalid.errors)
                serializer = serializer_class(acl, data={'workflow': None}, partial=True)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                serializer.save()
                self.assertIsNone(acl.workflow_id)
                instance.refresh_from_db()
                self.assertEqual(instance.version_id, internal.active_version_id)
                self.assertEqual(list(ApprovalTask.objects.filter(node_instance__instance=instance).values_list(
                    'pk', 'assignee_id', 'state',
                )), tasks)
                detail = WorkflowInstanceDetailSerializer(instance).data
                self.assertTrue(detail['workflow_is_system'])
                task = ApprovalTask.objects.get(node_instance__instance=instance, assignee=self.alice)
                self.engine.approve(task, self.alice)
                instance.refresh_from_db()
                self.assertEqual(instance.state, 'approved')

    def test_internal_workflows_cannot_be_bound_by_public_serializers(self):
        for model, serializer_class, ticket_type in self.cases:
            org_id = Organization.ROOT_ID if model is LoginACL else str(self.org.pk)
            workflow = get_system_workflow(org_id, ticket_type, [self.alice])
            serializer = serializer_class(data={'workflow': str(workflow.pk)}, partial=True)
            self.assertFalse(serializer.is_valid())
            self.assertIn('workflow', serializer.errors)
        internal = get_system_workflow(str(self.org.pk), 'general', [self.alice])
        serializer = TicketApplySerializer(context={'request': SimpleNamespace(user=self.applicant)})
        with self.assertRaises(ValidationError) as error:
            serializer.validate({'org_id': str(self.org.pk), 'type': 'general', 'workflow_id': internal.pk})
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
        role, _ = Role.objects.get_or_create(id=BuiltinRole.org_admin.id,
                                            defaults={'name': 'OrgAdmin', 'scope': 'org', 'builtin': True})
        RoleBinding.objects_raw.create(user=self.alice, role=role, org=self.org, scope='org')
        self.alice.expire_rbac_perms_cache()
        response = self.request('create', data={'name': 'Local approval', 'type': 'command_confirm'}, method='post')
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
        self.assertNotIn(str(internal.pk), [item['id'] for item in self.request('list').data['results']])
        self.assertNotIn(str(internal.pk), [item['id'] for item in self.request(
            'options_list', data={'org_id': str(self.org.pk), 'type': 'command_confirm'},
        ).data])
        for action, method in [('retrieve', 'get'), ('versions', 'get'),
                               ('partial_update', 'patch'), ('publish', 'post')]:
            self.assertEqual(self.request(action, internal, method=method).status_code, 404)
        with tmp_to_org(self.other_org):
            other = Workflow.objects.create(name='Other org', type='command_confirm')
        self.assertEqual(self.request('partial_update', other, {'enabled': False}, method='patch').status_code, 404)
        response = self.request('create', data={'name': 'Global login', 'type': 'login_confirm'}, method='post')
        self.assertEqual(response.status_code, 400, response.data)
        response = self.request('options_list', data={'org_id': Organization.ROOT_ID, 'type': 'login_confirm'})
        self.assertEqual(response.status_code, 403, response.data)
        with tmp_to_root_org():
            response = self.request('create', data={'name': 'Global login', 'type': 'login_confirm'}, method='post')
            self.assertEqual(response.status_code, 403, response.data)
