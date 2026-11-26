from unittest.mock import patch

from django.db import transaction
from django.test import TestCase
from django.utils.translation import override
from rest_framework.test import force_authenticate

from acls.models import CommandFilterACL, LoginACL, LoginAssetACL
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.api.workflow import WorkflowViewSet
from tickets.models import Ticket, Workflow, WorkflowVersion
from tickets.tests import test_workflow as fixtures
from tickets.workflow.composition import compose_workflows
from tickets.workflow.publication import publish_workflow
from tickets.workflow.errors import WorkflowConfigurationError, WorkflowConflict
from users.models import User


class WorkflowOrganizationTests(TestCase):
    setUpTestData = fixtures.WorkflowTests.__dict__['setUpTestData']
    setUp = fixtures.WorkflowTests.setUp

    def global_workflow(self):
        with tmp_to_root_org():
            workflow = Workflow.objects.create(
                org_id=Organization.ROOT_ID, type='general', name='Shared approval',
                enabled=True, comment='Original comment',
            )
            definition = fixtures.approval_definition(
                [], approvers={'type': 'role', 'value': [str(self.role.pk)]},
            )
            publish_workflow(workflow, definition)
            publish_workflow(workflow, definition)
            workflow.refresh_from_db()
        return workflow

    def request(self, action, workflow=None, data=None, method='get'):
        request = getattr(self.factory, method)('/', data or {}, format='json')
        force_authenticate(request, self.alice)
        with transaction.atomic(), patch.object(User, 'has_perms', return_value=True):
            return WorkflowViewSet.as_view({method: action})(
                request, **({'pk': str(workflow.pk)} if workflow else {}),
            )

    def test_management_lists_inherited_flows_and_local_overrides_only(self):
        inherited = self.global_workflow()
        local = Workflow.objects.create(type='general', name='Local approval')
        with tmp_to_org(self.other_org):
            other = Workflow.objects.create(type='general', name='Other organization approval')
        response = self.request('list', data={'type': 'general'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row['id']: (row['org_id'], row['org_name']) for row in response.data['results']}, {
            str(inherited.pk): (Organization.ROOT_ID, str(Organization.root().name)),
            str(local.pk): (str(self.org.pk), self.org.name),
        })
        self.assertEqual(self.request('retrieve', inherited).status_code, 200)
        self.assertEqual(self.request('versions', inherited).data['count'], 2)
        self.assertEqual(self.request('retrieve', other).status_code, 404)

        local.name = inherited.name.upper()
        local.save(update_fields=['name'])
        response = self.request('list', data={'type': 'general'})
        self.assertEqual([row['id'] for row in response.data['results']], [str(local.pk)])
        self.assertEqual(self.request('retrieve', inherited).status_code, 404)
        with tmp_to_root_org():
            response = self.request('list', data={'type': 'general'})
            self.assertEqual({row['id'] for row in response.data['results']},
                             {str(inherited.pk), str(local.pk), str(other.pk)})

    def test_editing_inherited_flow_copies_version_and_preserves_other_organizations(self):
        inherited = self.global_workflow()
        original_version = inherited.active_version
        ticket = Ticket.objects.create(type='general', title='Existing approval', applicant=self.applicant,
                                       org_id=self.org.pk)
        instance = self.engine.start(ticket, inherited, {})
        response = self.request('partial_update', inherited, {'enabled': False, 'expected_version': 2}, method='patch')
        self.assertEqual(response.status_code, 200, response.data)
        local = Workflow.objects.get(pk=response.data['id'])
        self.assertNotEqual(local.pk, inherited.pk)
        self.assertEqual(local.org_id, self.org.pk)
        self.assertEqual(local.name, inherited.name)
        self.assertEqual(local.comment, inherited.comment)
        self.assertFalse(local.enabled)
        self.assertIsNone(local.legacy_flow_id)
        self.assertEqual(local.active_version.number, 1)
        copied = local.active_version.as_definition()
        original = original_version.as_definition()
        self.assertEqual(copied['nodes'], original['nodes'])
        self.assertCountEqual(copied['edges'], original['edges'])

        response = self.request('publish', local, {
            'expected_version': 1, 'definition': fixtures.approval_definition([self.bob]),
        }, method='post')
        self.assertEqual(response.status_code, 201, response.data)
        response = self.request('partial_update', local, {'enabled': True}, method='patch')
        self.assertEqual(response.data['id'], str(local.pk))
        self.assertTrue(response.data['enabled'])
        with tmp_to_root_org():
            inherited.refresh_from_db()
        self.assertTrue(inherited.enabled)
        self.assertEqual(inherited.active_version_id, original_version.pk)
        self.assertEqual(inherited.versions.count(), 2)
        instance.refresh_from_db()
        self.assertEqual(instance.version_id, original_version.pk)
        self.assertEqual(instance.state, 'running')
        with tmp_to_org(self.other_org):
            self.assertEqual(self.request('retrieve', local).status_code, 404)
            self.assertEqual(self.request('retrieve', inherited).status_code, 200)

    def test_stale_inherited_version_does_not_create_a_local_override(self):
        inherited = self.global_workflow()
        response = self.request('partial_update', inherited, {
            'name': inherited.name, 'expected_version': 1,
        }, method='patch')
        self.assertEqual(response.status_code, 409, response.data)
        self.assertFalse(Workflow.objects.filter(type='general').exists())

    def test_delete_unused_workflow_and_all_its_versions(self):
        draft = Workflow.objects.create(type='general', name='Draft')
        self.assertEqual(self.request('destroy', draft, method='delete').status_code, 204)
        shared = self.global_workflow()
        self.assertEqual(self.request('destroy', shared, method='delete').status_code, 404)
        with tmp_to_root_org():
            self.assertEqual(self.request('destroy', shared, method='delete').status_code, 204)
            self.assertFalse(Workflow.objects.filter(pk__in=[draft.pk, shared.pk]).exists())
            self.assertFalse(WorkflowVersion.objects.filter(workflow_id=shared.pk).exists())

    def test_delete_preserves_acl_reference_until_removed(self):
        workflow = Workflow.objects.create(type='login_asset_confirm', name='ACL approval')
        version = publish_workflow(workflow, fixtures.approval_definition([self.alice]))
        acl = LoginAssetACL.objects.create(name='Review assets', workflow=workflow)
        response = self.request('destroy', workflow, method='delete')
        self.assertEqual(response.data['code'], 'referenced_by_others')
        self.assertIn(str(acl._meta.verbose_name), response.data['detail'])
        workflow.refresh_from_db()
        self.assertEqual(workflow.active_version_id, version.pk)
        acl.workflow = None
        acl.save(update_fields=['workflow'])
        self.assertEqual(self.request('destroy', workflow, method='delete').status_code, 204)

    def test_references_identify_each_rule_and_paginate_without_other_workflows(self):
        shared = self.global_workflow()
        with tmp_to_root_org():
            login = LoginACL.objects.create(name='User login rule', workflow=shared)
            with tmp_to_org(self.org):
                asset = LoginAssetACL.objects.create(name='Asset login rule', workflow=shared)
                command = CommandFilterACL.objects.create(name='Command rule', workflow=shared)
                LoginAssetACL.objects.create(name='Unrelated rule')
            with patch.object(User, 'has_perm', return_value=True):
                first = self.request('references', shared, {'limit': 2})
                second = self.request('references', shared, {'limit': 2, 'offset': 2})
            self.assertEqual(first.data['count'], 3)
            rows = list(first.data['results']) + list(second.data['results'])
            self.assertEqual({(r['record_name'], str(r['id']), r['record_org']) for r in rows}, {
                (login.name, str(login.pk), Organization.ROOT_ID),
                (asset.name, str(asset.pk), str(self.org.pk)),
                (command.name, str(command.pk), str(self.org.pk)),
            })
        with tmp_to_org(self.other_org), patch.object(User, 'has_perm', return_value=False):
            self.assertEqual(self.request('references', shared).data['count'], 0)

    def test_references_resolve_combined_history_and_enforce_ticket_visibility(self):
        workflow = Workflow.objects.create(type='login_asset_confirm', name='Source')
        version = publish_workflow(workflow, fixtures.approval_definition([self.alice]))
        combined = Workflow.objects.create(type=workflow.type, name='Combined', is_system=True,
                                           migration_notes={'source_versions': [str(version.pk)]})
        mine = Ticket.objects.create(workflow=combined, title='My linked ticket', org_id=self.org.pk,
                                     serial_num='202612345', applicant=self.alice)
        private = Ticket.objects.create(workflow=workflow, title='Private ticket', org_id=self.org.pk,
                                        applicant=self.bob)
        with patch.object(User, 'has_perm', side_effect=lambda perm: perm == 'tickets.view_ticket'):
            data = self.request('references', workflow).data
        self.assertEqual({r['record_name'] for r in data['results']}, {mine.title, combined.name})
        row = next(r for r in data['results'] if r['kind'] == 'ticket')
        self.assertEqual((row['record_number'], row['ticket_type']), (mine.serial_num, mine.type))
        with patch.object(User, 'has_perm', return_value=True):
            rows = self.request('references', workflow).data['results']
        self.assertEqual({r['record_name'] for r in rows}, {mine.title, private.title, combined.name})

    def test_delete_preserves_workflow_used_by_an_older_ticket(self):
        shared = self.global_workflow()
        ticket = Ticket.objects.create(type='general', title='Existing approval', applicant=self.applicant,
                                       org_id=self.org.pk)
        instance = self.engine.start(ticket, shared, {})
        with tmp_to_root_org():
            latest = publish_workflow(shared, shared.active_version.as_definition())
            response = self.request('destroy', shared, method='delete')
            self.assertEqual(response.data['code'], 'referenced_by_others')
            shared.refresh_from_db()
            self.assertEqual(shared.active_version_id, latest.pk)
            instance.refresh_from_db()
            self.assertEqual(instance.version.workflow_id, shared.pk)
            with patch.object(User, 'has_perm', return_value=True):
                rows = self.request('references', shared).data['results']
            self.assertEqual([str(row['id']) for row in rows], [str(ticket.pk)])

    def test_delete_preserves_combined_workflow_source(self):
        source = Workflow.objects.create(type='login_asset_confirm', name='Source')
        version = publish_workflow(source, fixtures.approval_definition([self.alice]))
        with tmp_to_org(self.other_org):
            Workflow.objects.create(type=source.type, name='Combined', is_system=True,
                                    migration_notes={'source_versions': [str(version.pk)]})
        response = self.request('destroy', source, method='delete')
        self.assertEqual(response.data['code'], 'referenced_by_others')
        self.assertTrue(source.versions.filter(pk=version.pk).exists())

    def test_combination_cannot_attach_a_concurrently_deleted_source(self):
        workflows = []
        for name in ('First', 'Second'):
            source = Workflow.objects.create(type='login_asset_confirm', name=name)
            publish_workflow(source, fixtures.approval_definition([self.alice]))
            source.refresh_from_db()
            workflows.append(source)
        self.assertEqual(self.request('destroy', source, method='delete').status_code, 204)
        with self.assertRaises(WorkflowConflict):
            compose_workflows(workflows, self.org.pk, source.type)

    def test_copy_with_invalid_local_cc_rolls_back_the_override(self):
        inherited = self.global_workflow()
        definition = inherited.active_version.as_definition()
        definition['nodes'].insert(1, {'id': 'cc', 'type': 'cc', 'config': {'users': [str(self.outsider.pk)]}})
        definition['edges'] = [['start', 'cc'], ['cc', 'approval_0'], ['approval_0', 'end']]
        with tmp_to_root_org():
            publish_workflow(inherited, definition)
        response = self.request('partial_update', inherited, {'enabled': False}, method='patch')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Workflow.objects.filter(type='general').exists())

    def test_inherited_and_other_organization_versions_cannot_be_published_directly(self):
        inherited = self.global_workflow()
        data = {'expected_version': 2, 'definition': fixtures.approval_definition([self.bob])}
        self.assertEqual(self.request('publish', inherited, data, method='post').status_code, 404)
        with tmp_to_org(self.other_org):
            other = Workflow.objects.create(type='general', name='Other organization approval')
        self.assertEqual(self.request('partial_update', other, {'enabled': False}, method='patch').status_code, 404)
        self.assertEqual(self.request('publish', other, data, method='post').status_code, 404)

    def test_root_edit_keeps_global_workflow_identity(self):
        inherited = self.global_workflow()
        with tmp_to_root_org():
            response = self.request('partial_update', inherited, {'enabled': False}, method='patch')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['id'], str(inherited.pk))
            inherited.refresh_from_db()
        self.assertFalse(inherited.enabled)
        self.assertEqual(inherited.org_id, Organization.ROOT_ID)

    def test_login_workflow_creation_and_type_changes_require_global_organization(self):
        data = {'name': 'Login approval', 'type': 'login_confirm'}
        response = self.request('create', data=data, method='post')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Workflow.objects.filter(type='login_confirm').exists())
        draft = Workflow.objects.create(name='Local draft', type='apply_asset')
        response = self.request('partial_update', draft, {'type': 'login_confirm'}, method='patch')
        self.assertEqual(response.status_code, 400, response.data)
        draft.refresh_from_db()
        self.assertEqual(draft.type, 'apply_asset')
        self.assertEqual(self.request('create', data={**data, 'type': 'login_asset_confirm'},
                                      method='post').status_code, 201)
        with tmp_to_root_org():
            response = self.request('create', data=data, method='post')
            self.assertEqual(response.status_code, 201, response.data)
            workflow = Workflow.objects.get(pk=response.data['id'])
            self.assertEqual(workflow.org_id, Organization.ROOT_ID)
            response = self.request('publish', workflow, {
                'expected_version': 0, 'definition': fixtures.approval_definition([self.alice]),
            }, method='post')
            self.assertEqual(response.status_code, 201, response.data)
            response = self.request('partial_update', workflow, {'enabled': True}, method='patch')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(response.data['enabled'])
        self.assertEqual(self.request('retrieve', workflow).status_code, 200)
        response = self.request('partial_update', workflow, {'comment': 'Local override'}, method='patch')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Workflow.objects.filter(type='login_confirm').exists())

    def test_historical_local_login_workflow_is_preserved_but_cannot_be_republished(self):
        workflow = Workflow.objects.create(name='Historical login approval', type='general', enabled=True)
        definition = fixtures.approval_definition([self.alice])
        publish_workflow(workflow, definition)
        workflow.refresh_from_db()
        # Represent a local login definition created before the scope restriction.
        workflow.type = 'login_confirm'
        workflow.save(update_fields=['type'])
        original_version = workflow.active_version_id
        self.assertEqual(self.request('retrieve', workflow).status_code, 200)
        self.assertEqual(self.request('versions', workflow).data['count'], 1)
        response = self.request('publish', workflow, {'expected_version': 1, 'definition': definition}, method='post')
        self.assertEqual(response.status_code, 400, response.data)
        response = self.request('partial_update', workflow, {'enabled': True}, method='patch')
        self.assertEqual(response.status_code, 400, response.data)
        with tmp_to_root_org(), override('en'), self.assertRaisesMessage(
            WorkflowConfigurationError, 'global organization',
        ):
            publish_workflow(workflow, definition)
        workflow.refresh_from_db()
        self.assertEqual(workflow.org_id, self.org.pk)
        self.assertEqual(workflow.active_version_id, original_version)
        self.assertTrue(workflow.enabled)
        self.assertEqual(workflow.versions.count(), 1)
