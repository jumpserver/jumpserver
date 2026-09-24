from types import SimpleNamespace
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework import serializers
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Account
from orgs.utils import tmp_to_org
from perms.models import AssetPermission
from terminal.models import Session
from tickets.api.plugin import TicketTypeViewSet
from tickets.api.ticket import TicketViewSet
from tickets.models import Ticket
from tickets.plugins import get_ticket_plugin, ticket_plugins
from tickets.plugins.base import TicketPlugin
from tickets.plugins.registry import TicketPluginRegistry
from tickets.plugins.resources import RequestSerializer
from tickets.serializers.plugin import PluginTicketApplySerializer
from tickets.serializers.ticket.apply_asset import ApplyAssetSerializer
from tickets.tests.test_workflow_business import WorkflowBusinessTests
from tickets.workflow.business import submit_ticket


class ExampleParameters(RequestSerializer):
    reason = serializers.CharField()


class PluginRegistryTests(SimpleTestCase):
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
        self.assertEqual(metadata['execution_mode'], 'approval_only')
        self.assertEqual({f['name'] for f in metadata['fields']}, {'asset', 'accounts', 'duration'})
        self.assertNotIn('apply_users', {field.name for field in Ticket._meta.fields})


class TicketPluginTests(TestCase):
    setUpTestData = WorkflowBusinessTests.__dict__['setUpTestData']
    setUp = WorkflowBusinessTests.setUp
    workflow = WorkflowBusinessTests.workflow
    ticket = WorkflowBusinessTests.ticket
    task = WorkflowBusinessTests.task

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
            ('view_secret', {'asset': str(self.asset.pk), 'accounts': ['root']}),
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

    def test_uniform_asset_request_reuses_legacy_validation_and_grants_users(self):
        data = self.payload('apply_asset', apply_assets=[str(self.asset.pk)], apply_accounts=['root'],
                            apply_actions=['connect'], apply_users=[str(self.bob.pk), str(self.carol.pk)],
                            apply_date_start=timezone.now(), apply_date_expired=timezone.now() + timedelta(hours=1))
        # The public JSON envelope contains JSON values, just like an HTTP client.
        for field in ('apply_date_start', 'apply_date_expired'):
            data['request_data'][field] = data['request_data'][field].isoformat()
        serializer = self.serializer(data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        instance = submit_ticket(ticket)
        self.engine.approve(self.task(instance), self.alice)
        grant = AssetPermission.objects.get(pk=ticket.pk)
        self.assertEqual(set(grant.users.values_list('pk', flat=True)), {self.bob.pk, self.carol.pk})
        self.assertEqual(ticket.applicant_id, self.applicant.pk)

    def test_legacy_asset_submission_rejects_invalid_users_and_defaults_to_self(self):
        data = self.payload('apply_asset')['request_data']
        data.update(title='Access', org_id=self.org.id, workflow_id=str(self.workflow().pk),
                    apply_assets=[str(self.asset.pk)], apply_accounts=['root'], apply_actions=['connect'],
                    apply_date_start=timezone.now(), apply_date_expired=timezone.now() + timedelta(hours=1))
        context = {'request': SimpleNamespace(user=self.applicant)}
        for users in ([], [str(self.outsider.pk)], [str(uuid4())]):
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
        instance = submit_ticket(ticket)
        plugin = get_ticket_plugin('view_secret')
        with patch.object(plugin, 'execution_mode', 'automatic'), patch.object(plugin, 'on_approved') as handler:
            self.engine.approve(self.task(instance), self.alice)
            handler.assert_not_called()
        self.assertFalse(instance.events.filter(type='action.executed').exists())

    def test_authorized_users_are_plugin_parameters_and_granted_from_snapshot(self):
        ticket = self.ticket()
        ticket.request_data = {'apply_users': [str(self.bob.pk), str(self.carol.pk)]}
        ticket.save(update_fields=['request_data'])
        instance = submit_ticket(ticket)
        Ticket.objects.filter(pk=ticket.pk).update(request_data={'apply_users': [str(self.applicant.pk)]})
        self.assertEqual(len(instance.context['accounts']), 1)
        self.engine.approve(self.task(instance), self.alice)
        grant = AssetPermission.objects.get(pk=ticket.pk)
        self.assertEqual(set(grant.users.values_list('pk', flat=True)), {self.bob.pk, self.carol.pk})
        self.assertEqual(ticket.applicant_id, self.applicant.pk)

    def test_ineligible_authorized_user_prevents_any_grant(self):
        ticket = self.ticket()
        ticket.request_data = {'apply_users': [str(self.bob.pk), str(self.carol.pk)]}
        ticket.save(update_fields=['request_data'])
        instance = submit_ticket(ticket)
        type(self.bob).objects.filter(pk=self.bob.pk).update(is_active=False)
        self.assertEqual(self.engine.approve(self.task(instance), self.alice).state, 'error')
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_user_alias_uses_authorized_user_not_submitter(self):
        ticket = self.ticket()
        ticket.apply_accounts = ['@USER']
        ticket.request_data = {'apply_users': [str(self.bob.pk)]}
        ticket.save(update_fields=['apply_accounts', 'request_data'])
        instance = submit_ticket(ticket)
        self.assertEqual(instance.context['accounts'][0]['username'], self.bob.username)
        type(self.bob).objects.filter(pk=self.bob.pk).update(username='changed-name')
        self.assertEqual(self.engine.approve(self.task(instance), self.alice).state, 'error')

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
