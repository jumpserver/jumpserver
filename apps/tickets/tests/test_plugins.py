from types import SimpleNamespace
from datetime import timedelta
from importlib import import_module
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Account
from accounts.api.account.ticket_secret import AccountTicketSecretAPI, AccountTicketSecretRequestAPI
from orgs.utils import tmp_to_org, tmp_to_root_org
from django.apps import apps as django_apps
from django.db import connection, transaction
from perms.models import AssetPermission
from rbac.builtin import BuiltinRole
from rbac.models import Permission, Role, RoleBinding
from terminal.models import Session
from tickets.api.plugin import TicketTypeViewSet
from tickets.api.ticket import TicketViewSet
from tickets.api.workflow import WorkflowInstanceViewSet
from tickets.api.workflow import WorkflowViewSet
from tickets.models import Ticket, TicketBeneficiary, TicketSecretAccess, Workflow, ApprovalTask
from tickets.plugins import get_ticket_plugin, ticket_plugins
from tickets.plugins.base import TicketPlugin
from tickets.plugins.registry import TicketPluginRegistry
from tickets.plugins.resources import RequestSerializer
from tickets.serializers.plugin import PluginTicketApplySerializer
from tickets.serializers.workflow import WorkflowEventSerializer
from tickets.serializers.ticket.apply_asset import ApplyAssetSerializer
from tickets.serializers.ticket.ticket import TicketSerializer
from tickets.tests.test_workflow import WorkflowTests, approval_definition
from tickets.workflow.business import submit_ticket
from tickets.workflow.engine import WorkflowEngine
from tickets.workflow.publication import publish_workflow
from tickets.plugins.apply_asset.policy import supports_delegated_request
from users.models import User
from assets.models import Asset, Node


class ExampleParameters(RequestSerializer):
    reason = serializers.CharField()


class PluginRegistryTests(SimpleTestCase):
    def test_default_result_resources_are_linkless_snapshots(self):
        resource = {'type': 'example', 'id': '123', 'name': 'Original', 'url': '/stale-link'}
        event = SimpleNamespace(data={'resources': [resource]})
        result = TicketPlugin().get_result_resources(None, event, None)
        self.assertEqual(result, [{'type': 'example', 'id': '123', 'name': 'Original'}])
        result[0]['name'] = 'Updated'
        self.assertEqual(resource['name'], 'Original')
        self.assertEqual(TicketPlugin().get_result_resources(None, SimpleNamespace(data={}), None), [])

    def test_discovery_is_repeatable_and_duplicate_types_fail(self):
        before = [p.type for p in ticket_plugins.all()]
        ticket_plugins.discover()
        self.assertEqual(before, [p.type for p in ticket_plugins.all()])
        registry = TicketPluginRegistry()
        registry.register(get_ticket_plugin('apply_asset'))
        with self.assertRaises(ImproperlyConfigured):
            registry.register(get_ticket_plugin('apply_asset'))

    def test_catalogue_exposes_fields_and_honest_execution_mode(self):
        metadata = get_ticket_plugin('view_secret').metadata()
        self.assertEqual(metadata['execution_mode'], 'automatic')
        self.assertEqual(metadata['creation_modes'], ['manual', 'operation'])
        self.assertEqual({f['name'] for f in metadata['fields']}, {'asset', 'accounts', 'duration'})
        self.assertNotIn('apply_users', {field.name for field in Ticket._meta.fields})

    def test_delegated_workflow_rejects_a_branch_that_skips_organization_admin(self):
        definition = {
            'nodes': [
                {'id': 'start', 'type': 'start'},
                {'id': 'branch', 'type': 'condition'},
                {'id': 'admin', 'type': 'approval', 'config': {'approvers': {'type': 'org_admin'}}},
                {'id': 'end', 'type': 'end'},
            ],
            'edges': [{'source': 'start', 'target': 'branch'},
                      {'source': 'branch', 'target': 'admin'},
                      {'source': 'branch', 'target': 'end'},
                      {'source': 'admin', 'target': 'end'}],
        }
        version = SimpleNamespace(published_at=timezone.now(), as_definition=lambda: definition)
        self.assertFalse(supports_delegated_request(version))
        definition['edges'][2]['target'] = 'admin'
        self.assertTrue(supports_delegated_request(version))


class TicketPluginTests(TestCase):
    setUpTestData = WorkflowTests.__dict__['setUpTestData']

    def setUp(self):
        scope = tmp_to_org(self.org)
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        for user in (self.applicant, self.alice, self.bob, self.carol):
            user.expire_rbac_perms_cache()
        self.engine = WorkflowEngine()
        self.asset = Asset.objects.create(name='Requested asset', address='192.0.2.10', platform=self.platform,
                                          owner=self.alice)
        self.node = Node.objects.create(key='900', value='Requested node')
        self.asset.nodes.add(self.node)

    def workflow(self, ticket_type='apply_asset', definition=None, **config):
        flow = Workflow.objects.create(name=str(uuid4()), type=ticket_type)
        publish_workflow(flow, definition or approval_definition([self.alice], **config))
        flow.refresh_from_db()
        flow.enabled = True
        flow.save(update_fields=['enabled'])
        return flow

    def delegated_workflow(self, **config):
        admin, _ = Role.objects.get_or_create(id=BuiltinRole.org_admin.id,
                                              defaults={'name': 'OrgAdmin', 'scope': 'org'})
        RoleBinding.objects_raw.get_or_create(user=self.alice, role=admin, org=self.org,
                                              defaults={'scope': 'org'})
        definition = approval_definition([self.alice], **config)
        definition['nodes'][1]['config']['approvers'] = {'type': 'org_admin'}
        return self.workflow(definition=definition)

    def grant_delegation(self):
        permission = Permission.objects.get(codename='apply_asset_for_others', content_type__model='workflow')
        role = Role.objects.create(name=str(uuid4()), scope='org')
        role.permissions.add(permission)
        RoleBinding.objects_raw.create(user=self.applicant, role=role, org=self.org, scope='org')
        self.applicant.expire_rbac_perms_cache()
        self.applicant = User.objects.get(pk=self.applicant.pk)

    def ticket(self, workflow=None):
        return Ticket.objects.create(
            title='Asset access', type='apply_asset', applicant=self.applicant, org_id=self.org.id,
            workflow=workflow or self.workflow(), request_data={
                'apply_users': [str(self.applicant.pk)], 'apply_assets': [str(self.asset.pk)],
                'apply_accounts': ['root'], 'apply_actions': 2,
                'apply_date_start': timezone.now().isoformat(),
                'apply_date_expired': (timezone.now() + timedelta(hours=2)).isoformat(),
            },
        )

    def task(self, instance, user=None):
        return ApprovalTask.objects.get(node_instance__instance=instance, assignee=user or self.alice,
                                        state='pending')

    def payload(self, ticket_type='view_secret', **parameters):
        return {'type': ticket_type, 'title': 'Plugin request', 'org_id': self.org.id,
                'workflow_id': str(self.workflow(ticket_type).pk), 'request_data': parameters}

    def serializer(self, data, user=None):
        return PluginTicketApplySerializer(data=data, context={'request': SimpleNamespace(user=user or self.applicant)})

    def create_account(self):
        return Account.objects.create(asset=self.asset, name='root', username='root', secret='never-in-ticket')

    def test_common_plugins_submit_approve_and_do_not_claim_execution(self):
        self.create_account()
        session = Session.objects.create(user_id=str(self.applicant.pk), user='Applicant',
                                         asset_id=str(self.asset.pk), asset='Asset', account='root', org_id=self.org.id)
        for ticket_type, parameters in [
            ('change_secret', {'asset': str(self.asset.pk), 'accounts': ['root']}),
            ('file_transfer', {'asset': str(self.asset.pk), 'accounts': ['root'],
                               'direction': 'download', 'paths': ['/var/log/app.log']}),
            ('download_replay', {'session': str(session.pk)}),
        ]:
            with self.subTest(ticket_type=ticket_type):
                serializer = self.serializer(self.payload(ticket_type, **parameters))
                self.assertTrue(serializer.is_valid(), serializer.errors)
                ticket = serializer.save()
                instance = submit_ticket(ticket)
                self.assertEqual(ticket.type, ticket_type)
                self.assertNotIn('never-in-ticket', str(instance.context))
                self.assertEqual(instance.context['request']['type'], ticket_type)
                self.engine.approve(self.task(instance), self.alice)
                ticket.refresh_from_db()
                self.assertEqual(ticket.state, 'approved')
                self.assertFalse(instance.events.filter(type='action.executed').exists())
                self.assertEqual(PluginTicketApplySerializer(ticket).data['execution_mode'], 'approval_only')

    def test_payload_rejects_secrets_unknown_accounts_and_cross_org_assets(self):
        self.create_account()
        base = self.payload(asset=str(self.asset.pk), accounts=['root'])
        for changes in [{'secret': 'do-not-store'}, {'asset': str(uuid4())}, {'accounts': ['missing']},
                        {'accounts': ['@ALL']}, {'duration': 0}, {'applicant': str(self.bob.pk)}]:
            with self.subTest(changes=changes):
                data = {**base, 'request_data': {**base['request_data'], **changes}}
                serializer = self.serializer(data)
                self.assertFalse(serializer.is_valid())
        with tmp_to_org(self.other_org):
            from assets.models import Asset
            asset = Asset.objects.create(name='Other asset', address='192.0.2.99', platform=self.platform)
        serializer = self.serializer({**base, 'request_data': {'asset': str(asset.pk), 'accounts': ['root']}})
        self.assertFalse(serializer.is_valid())

    def test_system_types_and_forged_applicant_cannot_use_self_service(self):
        for ticket_type in ('login_confirm', 'login_asset_confirm', 'command_confirm', 'general'):
            serializer = self.serializer(self.payload(ticket_type))
            self.assertFalse(serializer.is_valid())
        self.create_account()
        data = self.payload(asset=str(self.asset.pk), accounts=['root'])
        serializer = self.serializer({**data, 'applicant': str(self.bob.pk)})
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            serializer.is_valid(raise_exception=True)

    def test_replay_request_cannot_reference_other_users_session(self):
        session = Session.objects.create(user_id=str(self.bob.pk), user='Bob', asset='Asset', org_id=self.org.id)
        serializer = self.serializer(self.payload('download_replay', session=str(session.pk)))
        with patch.object(type(self.applicant), 'has_perm', return_value=False):
            self.assertFalse(serializer.is_valid())

    def test_uniform_endpoint_persists_type_and_scoped_payload(self):
        self.create_account()
        data = self.payload(asset=str(self.asset.pk), accounts=['root'])
        request = APIRequestFactory().post('/api/v1/tickets/tickets/open/', data, format='json')
        force_authenticate(request, self.applicant)
        with patch('rbac.permissions.RBACPermission.has_permission', return_value=True):
            response = TicketViewSet.as_view({'post': 'open'})(request)
        self.assertEqual(response.status_code, 201, response.data)
        ticket = Ticket.objects.get(pk=response.data['id'])
        self.assertEqual(ticket.type, 'view_secret')
        self.assertEqual(ticket.applicant_id, self.applicant.pk)
        self.assertEqual(ticket.workflow_instance.context['request']['accounts'], ['root'])

    def test_uniform_asset_request_grants_one_other_user(self):
        self.grant_delegation()
        data = self.payload('apply_asset', apply_assets=[str(self.asset.pk)], apply_accounts=['root'],
                            apply_actions=['connect'], apply_users=[str(self.bob.pk)],
                            apply_date_start=timezone.now(), apply_date_expired=timezone.now() + timedelta(hours=1))
        data['workflow_id'] = str(self.delegated_workflow().pk)
        # The public JSON envelope contains JSON values, just like an HTTP client.
        for field in ('apply_date_start', 'apply_date_expired'):
            data['request_data'][field] = data['request_data'][field].isoformat()
        serializer = self.serializer(data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        instance = submit_ticket(ticket)
        self.engine.approve(self.task(instance), self.alice)
        grant = AssetPermission.objects.get(pk=ticket.pk)
        self.assertEqual(set(grant.users.values_list('pk', flat=True)), {self.bob.pk})
        self.assertEqual(ticket.applicant_id, self.applicant.pk)
        self.assertTrue(TicketBeneficiary.objects.filter(ticket=ticket, user=self.bob).exists())

    def test_self_request_grants_only_applicant_and_excludes_them_from_approval(self):
        definition = approval_definition([self.applicant, self.alice], exclude_applicant=False)
        data = self.payload('apply_asset', apply_assets=[str(self.asset.pk)], apply_accounts=['root'],
                            apply_actions=['connect'], apply_date_start=timezone.now().isoformat(),
                            apply_date_expired=(timezone.now() + timedelta(hours=1)).isoformat())
        data['workflow_id'] = str(self.workflow(definition=definition).pk)
        serializer = self.serializer(data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        instance = submit_ticket(ticket)
        self.assertEqual(set(ApprovalTask.objects.filter(node_instance__instance=instance)
                             .values_list('assignee_id', flat=True)), {self.alice.pk})
        self.engine.approve(self.task(instance), self.alice)
        grant = AssetPermission.objects.get(pk=ticket.pk)
        self.assertEqual(list(grant.users.values_list('pk', flat=True)), [self.applicant.pk])

    def test_delegation_requires_permission_and_organization_admin_path(self):
        data = self.payload('apply_asset', apply_assets=[str(self.asset.pk)], apply_accounts=['root'],
                            apply_actions=['connect'], apply_users=[str(self.bob.pk)],
                            apply_date_start=timezone.now().isoformat(),
                            apply_date_expired=(timezone.now() + timedelta(hours=1)).isoformat())
        request = APIRequestFactory().post('/api/v1/tickets/tickets/open/', data, format='json')
        force_authenticate(request, self.applicant)
        # DRF's handled 403 rolls back the request transaction under PostgreSQL.
        with transaction.atomic(), patch('rbac.permissions.RBACPermission.has_permission', return_value=True):
            denied = TicketViewSet.as_view({'post': 'open'})(request)
        self.assertEqual(denied.status_code, 403, denied.data)

        self.grant_delegation()
        weak = self.serializer(data)
        self.assertFalse(weak.is_valid())
        self.assertIn('workflow_id', weak.errors)

        admin_flow = self.delegated_workflow()
        data['workflow_id'] = str(admin_flow.pk)
        allowed = self.serializer(data)
        self.assertTrue(allowed.is_valid(), allowed.errors)

    @override_settings(TICKET_APPLY_ASSET_SCOPE='all')
    def test_account_options_match_asset_and_submission_rules(self):
        from accounts.const import SecretType
        self.create_account()
        Account.objects.create(asset=self.asset, name='Other root', username='root', secret_type=SecretType.SSH_KEY)
        Account.objects.create(asset=self.asset, name='Disabled', username='disabled', is_active=False)
        Account.objects.create(asset=self.asset, name='Key only', username='key-only', secret_type=SecretType.SSH_KEY)
        for index in range(12):
            Account.objects.create(asset=self.asset, name=f'Account {index}', username=f'user-{index:02}')
        other = Asset.objects.create(name='Another asset', address='192.0.2.11', platform=self.platform)
        Account.objects.create(asset=other, name='Other account', username='other-asset')
        factory = APIRequestFactory()
        for ticket_type in ('change_secret', 'file_transfer', 'view_secret'):
            request = factory.get('/', {'org_id': self.org.id, 'asset': self.asset.id})
            force_authenticate(request, self.applicant)
            response = TicketTypeViewSet.as_view({'get': 'resource_options'})(request, pk=ticket_type)
            expected = ['root'] + [f'user-{index:02}' for index in range(12)]
            if ticket_type != 'view_secret':
                expected += ['disabled', 'key-only']
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data, sorted(expected))
            metadata = get_ticket_plugin(ticket_type).metadata()
            field = next(field for field in metadata['fields'] if field['name'] == 'accounts')
            self.assertEqual(field['resource'], 'account')
            serializer = get_ticket_plugin(ticket_type).get_request_serializer(
                context={'request': SimpleNamespace(user=self.applicant), 'org_id': self.org.id})
            self.assertEqual(serializer.validate({'asset': self.asset.id, 'accounts': response.data})['accounts'], response.data)
        request = factory.get('/', {'org_id': self.org.id, 'asset': other.id})
        force_authenticate(request, self.applicant)
        response = TicketTypeViewSet.as_view({'get': 'resource_options'})(request, pk='change_secret')
        self.assertEqual(response.data, ['other-asset'])

    @override_settings(TICKET_APPLY_ASSET_SCOPE='all')
    def test_account_options_reject_unavailable_assets_and_organizations(self):
        with tmp_to_org(self.other_org):
            other_asset = Asset.objects.create(name='Outside org', address='192.0.2.12', platform=self.platform)
        factory = APIRequestFactory()
        cases = [({'org_id': self.org.id}, 400),
                 ({'org_id': self.org.id, 'asset': 'invalid'}, 400),
                 ({'org_id': self.org.id, 'asset': str(uuid4())}, 400),
                 ({'org_id': self.org.id, 'asset': other_asset.id}, 400),
                 ({'org_id': self.other_org.id, 'asset': other_asset.id}, 403)]
        for params, expected_status in cases:
            request = factory.get('/', params)
            force_authenticate(request, self.applicant)
            response = TicketTypeViewSet.as_view({'get': 'resource_options'})(request, pk='change_secret')
            self.assertEqual(response.status_code, expected_status, response.data)
        with override_settings(TICKET_APPLY_ASSET_SCOPE='permed_valid'):
            request = factory.get('/', {'org_id': self.org.id, 'asset': self.asset.id})
            force_authenticate(request, self.applicant)
            response = TicketTypeViewSet.as_view({'get': 'resource_options'})(request, pk='change_secret')
            self.assertEqual(response.status_code, 400, response.data)

    def test_user_options_and_delegated_workflows_follow_permission(self):
        factory = APIRequestFactory()
        request = factory.get('/', {'org_id': self.org.id})
        force_authenticate(request, self.applicant)
        before = TicketTypeViewSet.as_view({'get': 'resource_options'})(request, pk='apply_asset')
        self.assertEqual([row['id'] for row in before.data], [self.applicant.pk])

        self.grant_delegation()
        request = factory.get('/', {'org_id': self.org.id})
        force_authenticate(request, self.applicant)
        after = TicketTypeViewSet.as_view({'get': 'resource_options'})(request, pk='apply_asset')
        self.assertIn(self.bob.pk, {row['id'] for row in after.data})

        weak = self.workflow()
        strong = self.delegated_workflow()
        request = factory.get('/', {'org_id': self.org.id, 'type': 'apply_asset',
                                    'beneficiary': str(self.bob.pk)})
        force_authenticate(request, self.applicant)
        response = WorkflowViewSet.as_view({'get': 'options_list'},
                                           permission_classes=[IsAuthenticated])(request)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn(str(strong.pk), {item['id'] for item in response.data})
        self.assertNotIn(str(weak.pk), {item['id'] for item in response.data})

    def test_beneficiary_cannot_approve_or_receive_transferred_task(self):
        admin_flow = self.delegated_workflow(allow_transfer=True, exclude_applicant=False)
        admin = Role.objects.get(pk=BuiltinRole.org_admin.id)
        RoleBinding.objects_raw.create(user=self.bob, role=admin, org=self.org, scope='org')
        ticket = self.ticket(admin_flow)
        ticket.request_data['apply_users'] = [str(self.bob.pk)]
        ticket.save(update_fields=['request_data'])
        instance = submit_ticket(ticket)
        self.assertEqual(set(ApprovalTask.objects.filter(node_instance__instance=instance)
                             .values_list('assignee_id', flat=True)), {self.alice.pk})
        from tickets.workflow.errors import WorkflowConfigurationError
        with self.assertRaises(WorkflowConfigurationError):
            self.engine.transfer(self.task(instance), self.alice, self.bob)
        # A pending task created before the exclusion rule was deployed is also blocked.
        old_task = ApprovalTask.objects.create(node_instance=self.task(instance).node_instance, assignee=self.bob)
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            self.engine.approve(old_task, self.bob)

    def test_beneficiary_can_read_ticket_and_instance_and_receives_result(self):
        self.grant_delegation()
        data = self.payload('apply_asset', apply_assets=[str(self.asset.pk)], apply_accounts=['root'],
                            apply_actions=['connect'], apply_users=[str(self.bob.pk)],
                            apply_date_start=timezone.now().isoformat(),
                            apply_date_expired=(timezone.now() + timedelta(hours=1)).isoformat())
        data['workflow_id'] = str(self.delegated_workflow().pk)
        serializer = self.serializer(data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        instance = submit_ticket(ticket)
        self.assertTrue(Ticket.get_user_related_tickets(self.bob).filter(pk=ticket.pk).exists())
        ticket_permission = Permission.objects.get(codename='view_ticket', content_type__model='ticket')
        role = Role.objects.create(name=str(uuid4()), scope='system')
        role.permissions.add(ticket_permission)
        RoleBinding.objects_raw.create(user=self.bob, role=role, scope='system')
        self.bob.expire_rbac_perms_cache()
        self.bob = User.objects.get(pk=self.bob.pk)
        request = APIRequestFactory().get('/api/v1/tickets/tickets/')
        force_authenticate(request, self.bob)
        response = TicketViewSet.as_view({'get': 'retrieve'})(request, pk=ticket.pk)
        self.assertEqual(response.status_code, 200, response.data)
        listing = APIRequestFactory().get('/api/v1/tickets/tickets/', {'beneficiary': str(self.bob.pk)})
        force_authenticate(listing, self.bob)
        response = TicketViewSet.as_view({'get': 'list'})(listing)
        self.assertEqual(response.status_code, 200, response.data)
        rows = response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertIn(str(ticket.pk), {str(item['id']) for item in rows})
        response = WorkflowInstanceViewSet.as_view({'get': 'retrieve'})(request, pk=instance.pk)
        self.assertEqual(response.status_code, 200, response.data)

        from tickets.workflow.business import deliver_event
        self.engine.approve(self.task(instance), self.alice)
        event = instance.events.get(type='workflow.completed')
        with patch('tickets.notifications.TicketProcessedToBeneficiaryMessage.publish_async') as beneficiary_notice, \
                patch('tickets.notifications.TicketProcessedToApplicantMessage.publish_async'), \
                patch('tickets.notifications.TicketUpdatedToCcUserMessage.publish_async'):
            deliver_event(event.pk)
        beneficiary_notice.assert_called_once()

    def test_historical_multi_user_tickets_keep_beneficiary_visibility(self):
        ticket = self.ticket()
        ticket.request_data['apply_users'] = [str(self.bob.pk), str(self.carol.pk)]
        ticket.save(update_fields=['request_data'])
        migration = import_module('tickets.migrations.0017_single_asset_beneficiary')
        migration.backfill_beneficiaries(django_apps, SimpleNamespace(connection=connection))
        self.assertEqual(set(ticket.beneficiaries.values_list('user_id', flat=True)),
                         {self.bob.pk, self.carol.pk})

    def test_legacy_asset_submission_rejects_invalid_users_and_defaults_to_self(self):
        data = self.payload('apply_asset')['request_data']
        data.update(title='Access', org_id=self.org.id, workflow_id=str(self.workflow().pk),
                    apply_assets=[str(self.asset.pk)], apply_accounts=['root'], apply_actions=['connect'],
                    apply_date_start=timezone.now(), apply_date_expired=timezone.now() + timedelta(hours=1))
        context = {'request': SimpleNamespace(user=self.applicant)}
        for users in ([], [str(self.outsider.pk)], [str(uuid4())],
                      [str(self.bob.pk), str(self.carol.pk)]):
            serializer = ApplyAssetSerializer(data={**data, 'apply_users': users}, context=context)
            self.assertFalse(serializer.is_valid())
        serializer = ApplyAssetSerializer(data=data, context=context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['request_data']['apply_users'], [str(self.applicant.pk)])

    def test_snapshot_details_survive_parameter_changes(self):
        self.create_account()
        serializer = self.serializer(self.payload(asset=str(self.asset.pk), accounts=['root']))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        submit_ticket(ticket)
        Ticket.objects.filter(pk=ticket.pk).update(request_data={'accounts': ['changed']})
        ticket.refresh_from_db()
        items = {item['name']: item['value'] for item in get_ticket_plugin(ticket.type).request_items(ticket)}
        self.assertEqual(items['accounts'], ['root'])

    def test_enabling_handler_does_not_execute_existing_approval_only_requests(self):
        self.create_account()
        serializer = self.serializer(self.payload(asset=str(self.asset.pk), accounts=['root']))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        plugin = get_ticket_plugin('view_secret')
        with patch.object(plugin, 'execution_mode', 'approval_only'):
            instance = submit_ticket(ticket)
        with patch.object(plugin, 'on_approved') as handler:
            self.engine.approve(self.task(instance), self.alice)
            handler.assert_not_called()
        self.assertFalse(instance.events.filter(type='action.executed').exists())

    def test_view_secret_approval_creates_scoped_grant_and_reveals_only_to_applicant(self):
        account = self.create_account()
        serializer = self.serializer(self.payload(asset=str(self.asset.pk), accounts=['root'], duration=600))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        instance = submit_ticket(ticket)
        self.assertNotIn(account.secret, str(instance.context))
        self.assertFalse(TicketSecretAccess.objects.filter(ticket=ticket).exists())
        self.engine.approve(self.task(instance), self.alice)
        ticket.refresh_from_db()
        grant = TicketSecretAccess.objects.get(ticket=ticket, account_id=account.pk)
        self.assertEqual((grant.user_id, grant.org_id), (self.applicant.pk, self.org.id))
        self.assertTrue(instance.events.filter(type='action.executed').exists())
        self.assertEqual(len(get_ticket_plugin('view_secret').get_available_actions(ticket, self.applicant)), 1)
        self.assertEqual(get_ticket_plugin('view_secret').get_available_actions(ticket, self.alice), [])

        def reveal(user, account_id=account.pk):
            request = APIRequestFactory().post('/', {'ticket_id': str(ticket.pk)}, format='json')
            force_authenticate(request, user)
            return AccountTicketSecretAPI.as_view()(request, pk=account_id)

        with override_settings(SECURITY_VIEW_AUTH_NEED_MFA=False):
            self.assertEqual(reveal(self.bob).status_code, 403)
            self.assertEqual(reveal(self.applicant, uuid4()).status_code, 403)
            response = reveal(self.applicant)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['secret'], 'never-in-ticket')
            self.assertEqual(response['Cache-Control'], 'no-store')
            self.assertTrue(instance.events.filter(type='secret.viewed', actor=self.applicant).exists())
            with override_settings(SECURITY_DISABLE_VIEW_SECRET=True):
                self.assertEqual(reveal(self.applicant).status_code, 403)
            TicketSecretAccess.objects.filter(pk=grant.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
            self.assertEqual(reveal(self.applicant).status_code, 403)

    def test_account_operation_starts_exact_password_ticket(self):
        account = self.create_account()
        workflow = self.workflow('view_secret')
        ticket_permission = Permission.objects.get(codename='view_ticket', content_type__model='ticket')
        role = Role.objects.create(name=str(uuid4()), scope='system')
        role.permissions.add(ticket_permission)
        RoleBinding.objects_raw.create(user=self.applicant, role=role, scope='system')
        self.applicant.expire_rbac_perms_cache()
        self.applicant = User.objects.get(pk=self.applicant.pk)
        endpoint = AccountTicketSecretRequestAPI.as_view()
        request = APIRequestFactory().get('/')
        force_authenticate(request, self.applicant)
        response = endpoint(request, pk=account.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['org_id'], self.org.id)
        self.assertIn(str(workflow.pk), [item['id'] for item in response.data['workflows']])

        request = APIRequestFactory().post('/', {'workflow_id': str(workflow.pk), 'duration': 600}, format='json')
        force_authenticate(request, self.applicant)
        response = endpoint(request, pk=account.pk)
        self.assertEqual(response.status_code, 201, response.data)
        ticket = Ticket.objects.get(pk=response.data['id'])
        self.assertEqual(ticket.origin, 'system')
        self.assertEqual(ticket.applicant_id, self.applicant.pk)
        self.assertEqual(ticket.request_data['accounts'], [account.username])
        self.assertEqual(ticket.workflow_instance.context['accounts'][0]['id'], str(account.pk))
        self.engine.approve(self.task(ticket.workflow_instance), self.alice)
        self.assertTrue(TicketSecretAccess.objects.filter(ticket=ticket, account_id=account.pk).exists())
        detail_request = APIRequestFactory().get('/api/v1/tickets/tickets/')
        force_authenticate(detail_request, self.applicant)
        detail = TicketViewSet.as_view({'get': 'retrieve'})(detail_request, pk=ticket.pk)
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual([item['account_id'] for item in detail.data['available_actions']], [str(account.pk)])
        self.assertEqual(detail.data['secret_access_status']['state'], 'available')
        with override_settings(SECURITY_DISABLE_VIEW_SECRET=True):
            hidden = TicketViewSet.as_view({'get': 'retrieve'})(detail_request, pk=ticket.pk)
            self.assertEqual(hidden.data['available_actions'], [])
            self.assertEqual(hidden.data['secret_access_status'], {'state': 'disabled'})

    def test_secret_access_status_uses_real_grants_and_distinguishes_unavailable_reasons(self):
        account = self.create_account()
        serializer = self.serializer(self.payload(asset=str(self.asset.pk), accounts=['root'], duration=600))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        instance = submit_ticket(ticket)
        plugin = get_ticket_plugin('view_secret')
        self.assertEqual(plugin.get_secret_access(ticket, self.applicant), ([], {'state': 'pending'}))
        for state in ('rejected', 'closed', 'expired', 'error'):
            ticket.state = state
            self.assertEqual(plugin.get_secret_access(ticket, self.applicant), ([], {'state': 'unapproved'}))
        self.engine.approve(self.task(instance), self.alice)
        ticket.refresh_from_db()
        grant = TicketSecretAccess.objects.get(ticket=ticket, account_id=account.pk)
        with CaptureQueriesContext(connection) as queries:
            actions, status = plugin.get_secret_access(ticket, self.applicant)
        self.assertEqual(status, {'state': 'available', 'expires_at': grant.expires_at.isoformat()})
        self.assertEqual([action['account_id'] for action in actions], [str(account.pk)])
        self.assertFalse(any('"accounts_account"."secret"' in query['sql'] for query in queries))
        self.assertEqual(plugin.get_secret_access(ticket, self.alice), ([], {'state': 'not_applicant'}))
        with override_settings(SECURITY_DISABLE_VIEW_SECRET=True):
            self.assertEqual(plugin.get_secret_access(ticket, self.applicant), ([], {'state': 'disabled'}))
            self.assertEqual(plugin.get_secret_access(ticket, self.alice), ([], {'state': 'not_applicant'}))

        expired_at = timezone.now() - timedelta(seconds=1)
        TicketSecretAccess.objects.filter(pk=grant.pk).update(expires_at=expired_at)
        self.assertEqual(plugin.get_secret_access(ticket, self.applicant),
                         ([], {'state': 'expired', 'expires_at': expired_at.isoformat()}))
        for changes in ({'is_active': False}, {'user_id': self.bob.pk}, {'org_id': self.other_org.id}):
            with self.subTest(changes=changes):
                TicketSecretAccess.objects.filter(pk=grant.pk).update(**changes)
                self.assertEqual(plugin.get_secret_access(ticket, self.applicant), ([], {'state': 'unavailable'}))
                TicketSecretAccess.objects.filter(pk=grant.pk).update(
                    is_active=True, user_id=self.applicant.pk, org_id=self.org.id,
                )
        Account.objects.filter(pk=account.pk).update(is_active=False)
        self.assertEqual(plugin.get_secret_access(ticket, self.applicant), ([], {'state': 'unavailable'}))
        Account.objects.filter(pk=account.pk).update(is_active=True)
        self.asset.is_active = False
        self.asset.save(update_fields=['is_active'])
        self.assertEqual(plugin.get_secret_access(ticket, self.applicant), ([], {'state': 'unavailable'}))
        self.asset.is_active = True
        self.asset.save(update_fields=['is_active'])
        User.objects.filter(pk=self.applicant.pk).update(is_active=False)
        self.assertEqual(plugin.get_secret_access(ticket, self.applicant), ([], {'state': 'unavailable'}))
        User.objects.filter(pk=self.applicant.pk).update(is_active=True)
        grant.delete()
        self.assertEqual(plugin.get_secret_access(ticket, self.applicant), ([], {'state': 'unavailable'}))

    def test_secret_access_status_only_serializes_on_password_ticket_detail_and_reuses_queries(self):
        self.create_account()
        serializer = self.serializer(self.payload(asset=str(self.asset.pk), accounts=['root']))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        context = {'request': SimpleNamespace(user=self.applicant), 'view': SimpleNamespace(action='retrieve')}
        plugin = get_ticket_plugin('view_secret')
        with patch.object(plugin, 'get_secret_access', wraps=plugin.get_secret_access) as access:
            data = TicketSerializer(ticket, context=context).data
            self.assertEqual(data['secret_access_status'], {'state': 'pending'})
            self.assertEqual(data['available_actions'], [])
            access.assert_called_once_with(ticket, self.applicant)
            access.reset_mock()
            data = TicketSerializer(ticket, context={**context, 'view': SimpleNamespace(action='list')}).data
            self.assertIsNone(data['secret_access_status'])
            self.assertEqual(data['available_actions'], [])
            self.assertIsNone(TicketSerializer(self.ticket(), context=context).data['secret_access_status'])
            access.assert_not_called()

    def test_authorized_users_are_plugin_parameters_and_granted_from_snapshot(self):
        ticket = self.ticket(self.delegated_workflow())
        ticket.request_data['apply_users'] = [str(self.bob.pk)]
        ticket.save(update_fields=['request_data'])
        instance = submit_ticket(ticket)
        Ticket.objects.filter(pk=ticket.pk).update(request_data={'apply_users': [str(self.applicant.pk)]})
        self.assertEqual(len(instance.context['accounts']), 1)
        self.engine.approve(self.task(instance), self.alice)
        grant = AssetPermission.objects.get(pk=ticket.pk)
        self.assertEqual(set(grant.users.values_list('pk', flat=True)), {self.bob.pk})
        self.assertEqual(ticket.applicant_id, self.applicant.pk)

    def test_ineligible_authorized_user_prevents_any_grant(self):
        ticket = self.ticket(self.delegated_workflow())
        ticket.request_data['apply_users'] = [str(self.bob.pk)]
        ticket.save(update_fields=['request_data'])
        instance = submit_ticket(ticket)
        type(self.bob).objects.filter(pk=self.bob.pk).update(is_active=False)
        self.assertEqual(self.engine.approve(self.task(instance), self.alice).state, 'error')
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_user_alias_uses_authorized_user_not_submitter(self):
        ticket = self.ticket(self.delegated_workflow())
        ticket.request_data['apply_accounts'] = ['@USER']
        ticket.request_data['apply_users'] = [str(self.bob.pk)]
        ticket.save(update_fields=['request_data'])
        instance = submit_ticket(ticket)
        self.assertEqual(instance.context['accounts'][0]['username'], self.bob.username)
        type(self.bob).objects.filter(pk=self.bob.pk).update(username='changed-name')
        self.assertEqual(self.engine.approve(self.task(instance), self.alice).state, 'error')

    def result_event(self, instance, user=None):
        request = APIRequestFactory().get('/')
        force_authenticate(request, user or self.applicant)
        response = WorkflowInstanceViewSet.as_view({'get': 'events'})(request, pk=str(instance.pk))
        self.assertEqual(response.status_code, 200)
        events = response.data['results'] if isinstance(response.data, dict) else response.data
        return next(event for event in events if event['type'] == 'action.executed')

    def grant_result_permission(self, org=None):
        permission = Permission.objects.get(codename='view_assetpermission', content_type__app_label='perms')
        role = Role.objects.create(name=str(uuid4()), scope='org')
        role.permissions.add(permission)
        RoleBinding.objects_raw.create(user=self.alice, role=role, org=org or self.org, scope='org')
        self.alice.expire_rbac_perms_cache()
        self.alice = User.objects.get(pk=self.alice.pk)

    def test_action_result_records_grant_and_resolves_links_for_current_viewer(self):
        ticket = self.ticket()
        instance = submit_ticket(ticket)
        self.engine.approve(self.task(instance), self.alice)
        grant = AssetPermission.objects.get(pk=ticket.pk)
        snapshot = {'type': 'asset_permission', 'id': str(grant.pk), 'name': grant.name}
        event = self.result_event(instance)
        self.assertEqual(event['data']['resources'], [snapshot])
        self.assertEqual(event['resources'][0]['name'], grant.name)
        self.assertNotIn('url', event['resources'][0])

        self.grant_result_permission()
        AssetPermission.objects.filter(pk=grant.pk).update(name='Renamed after execution')
        linked = self.result_event(instance, self.alice)['resources'][0]
        self.assertEqual(linked['name'], snapshot['name'])
        self.assertEqual(linked['url'], f'/ui/#/console/perms/asset-permissions/{grant.pk}?oid={self.org.id}')

        grant.delete()
        deleted = self.result_event(instance, self.alice)['resources'][0]
        self.assertEqual(deleted['name'], snapshot['name'])
        self.assertNotIn('url', deleted)
        self.assertEqual(instance.events.get(type='action.executed').data['resources'], [snapshot])

    def test_action_result_does_not_use_permissions_from_another_organization(self):
        ticket = self.ticket()
        instance = submit_ticket(ticket)
        self.engine.approve(self.task(instance), self.alice)
        self.grant_result_permission(self.other_org)
        with tmp_to_org(self.other_org):
            self.assertTrue(self.alice.has_perm('perms.view_assetpermission'))
        event = instance.events.get(type='action.executed')
        with tmp_to_root_org():
            result = WorkflowEventSerializer(event, context={
                'request': SimpleNamespace(user=self.alice), 'workflow_instance': instance,
            }).data
        self.assertNotIn('url', result['resources'][0])

    def test_action_result_does_not_link_a_grant_moved_to_another_organization(self):
        ticket = self.ticket()
        instance = submit_ticket(ticket)
        self.engine.approve(self.task(instance), self.alice)
        self.grant_result_permission()
        AssetPermission.objects.filter(pk=ticket.pk).update(org_id=self.other_org.id)
        self.assertNotIn('url', self.result_event(instance, self.alice)['resources'][0])

    def test_legacy_action_result_resolves_existing_grant_without_replaying_effect(self):
        ticket = self.ticket()
        instance = submit_ticket(ticket)
        self.engine.approve(self.task(instance), self.alice)
        event = instance.events.get(type='action.executed')
        event.data.pop('resources')
        event.save(update_fields=['data'])
        self.grant_result_permission()
        with patch('tickets.plugins.apply_asset.handler.on_approved') as handler:
            resource = self.result_event(instance, self.alice)['resources'][0]
            self.assertEqual(resource['id'], str(ticket.pk))
            self.assertIn('url', resource)
            AssetPermission.objects.get(pk=ticket.pk).delete()
            self.assertEqual(self.result_event(instance, self.alice)['resources'], [])
            handler.assert_not_called()
        event.refresh_from_db()
        self.assertNotIn('resources', event.data)

    def test_automatic_plugin_can_present_multiple_business_results(self):
        class ExamplePlugin(TicketPlugin):
            type, label, self_service = 'test_results', 'Example results', True
            execution_mode = 'automatic'
            request_serializer = 'tickets.tests.test_plugins.ExampleParameters'

            def on_approved(self, instance, ticket):
                return {'resources': [{'type': 'job', 'id': '1', 'name': 'First job'},
                                      {'type': 'job', 'id': '2', 'name': 'Second job'}]}

            def get_result_resources(self, instance, event, user):
                resources = super().get_result_resources(instance, event, user)
                for resource in resources:
                    resource['label'] = 'Job'
                return resources

        ticket_plugins.register(ExamplePlugin())
        self.addCleanup(ticket_plugins._plugins.pop, 'test_results')
        serializer = self.serializer(self.payload('test_results', reason='Need jobs'))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = submit_ticket(serializer.save())
        self.engine.approve(self.task(instance), self.alice)
        self.assertEqual(self.result_event(instance)['resources'], [
            {'type': 'job', 'id': '1', 'name': 'First job', 'label': 'Job'},
            {'type': 'job', 'id': '2', 'name': 'Second job', 'label': 'Job'},
        ])

    def test_new_plugin_needs_no_enum_model_or_route(self):
        class ExamplePlugin(TicketPlugin):
            type, label, self_service = 'test_example', 'Example', True
            request_serializer = 'tickets.tests.test_plugins.ExampleParameters'

        ticket_plugins.register(ExamplePlugin())
        self.addCleanup(ticket_plugins._plugins.pop, 'test_example')
        self.assertEqual(get_ticket_plugin('test_example').metadata()['fields'][0]['name'], 'reason')
        serializer = self.serializer(self.payload('test_example', reason='Need access'))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        instance = submit_ticket(ticket)
        self.engine.approve(self.task(instance), self.alice)
        ticket.refresh_from_db()
        self.assertEqual((ticket.type, ticket.state), ('test_example', 'approved'))

    def test_catalogue_and_user_options(self):
        factory = APIRequestFactory()
        request = factory.get('/api/v1/tickets/ticket-types/')
        force_authenticate(request, self.applicant)
        response = TicketTypeViewSet.as_view({'get': 'list'})(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('view_secret', {item['type'] for item in response.data})
        for org_id, status in [(self.org.id, 200), (self.other_org.id, 403)]:
            request = factory.get('/', {'org_id': org_id})
            force_authenticate(request, self.applicant)
            response = TicketTypeViewSet.as_view({'get': 'resource_options'})(request, pk='apply_asset')
            self.assertEqual(response.status_code, status)
