from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Account
from assets.models import Asset
from orgs.utils import tmp_to_org, tmp_to_root_org
from perms.models import AssetPermission
from rbac.models import Permission, Role, RoleBinding
from tickets.api.workflow import ApprovalTaskViewSet
from tickets.models import TicketSecretAccess
from tickets.plugins import get_ticket_plugin
from tickets.serializers.ticket.ticket import TicketSerializer
from tickets.tests import test_plugins
from tickets.tests.test_workflow import approval_definition
from tickets.workflow.business import submit_ticket
from tickets.workflow.resources import adjustment_status, resource_availability


@override_settings(TICKET_APPLY_ASSET_SCOPE='permed_valid')
class ResourceAdjustmentTests(TestCase):
    setUpTestData = test_plugins.TicketPluginTests.__dict__['setUpTestData']
    setUp = test_plugins.TicketPluginTests.setUp
    workflow = test_plugins.TicketPluginTests.workflow
    serializer = test_plugins.TicketPluginTests.serializer
    payload = test_plugins.TicketPluginTests.payload
    task = test_plugins.TicketPluginTests.task
    create_account = test_plugins.TicketPluginTests.create_account

    def grant_query(self, user=None, org=None):
        user, org = user or self.alice, org or self.org
        role = Role.objects.create(name=str(uuid4()), scope='org')
        role.permissions.add(*Permission.objects.filter(codename__in=['view_asset', 'view_account', 'view_node'],
                                                        content_type__app_label__in=['assets', 'accounts']))
        RoleBinding.objects_raw.create(user=user, role=role, org=org, scope='org')
        user.expire_rbac_perms_cache()

    def resources(self, ticket_type='view_secret'):
        if ticket_type == 'view_secret':
            return {'asset': str(self.asset.pk), 'accounts': ['root'], 'duration': 600}
        return {'apply_assets': [str(self.asset.pk)], 'apply_nodes': [], 'apply_accounts': ['root'],
                'apply_actions': ['connect'], 'apply_date_start': timezone.now().isoformat(),
                'apply_date_expired': (timezone.now() + timedelta(hours=1)).isoformat()}

    def deferred(self, ticket_type='view_secret', definition=None):
        values = self.resources(ticket_type)
        if ticket_type == 'view_secret':
            values.pop('asset')
            values.pop('accounts')
        else:
            values.update(apply_assets=[], apply_accounts=[])
        data = self.payload(ticket_type, **values, resource_description='Production database access for incident analysis')
        if definition:
            data['workflow_id'] = str(self.workflow(ticket_type, definition=definition).pk)
        serializer = self.serializer(data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        return ticket, submit_ticket(ticket)

    @override_settings(TICKET_APPLY_ASSET_SCOPE='all')
    def owner_request(self, ticket_type='view_secret', **config):
        definition = approval_definition([], approvers={'type': 'asset_owner'}, **config)
        data = self.payload(ticket_type, **self.resources(ticket_type))
        data['workflow_id'] = str(self.workflow(ticket_type, definition=definition).pk)
        serializer = self.serializer(data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        return ticket, submit_ticket(ticket)

    def call(self, task, data=None, *, user=None, operation='adjust_resources'):
        method = 'get' if operation == 'resource_options' else 'post'
        request = getattr(APIRequestFactory(), method)('/', data or {}, format='json')
        force_authenticate(request, user or self.alice)
        with transaction.atomic():
            return ApprovalTaskViewSet.as_view({method: operation})(request, pk=task.pk)

    def save(self, instance, *, revision=0, user=None, resources=None):
        return self.call(self.task(instance, user), {
            'expected_revision': revision, 'reason': 'Matched the requested production host',
            'resources': resources or self.resources(instance.ticket.type)}, user=user)

    def test_both_types_save_separately_then_approve_and_preserve_original_description(self):
        self.create_account()
        self.grant_query()
        for kind in ('view_secret', 'apply_asset'):
            with self.subTest(kind=kind):
                ticket, instance = self.deferred(kind)
                task = self.task(instance)
                self.assertEqual(self.call(task, operation='approve').status_code, 409)
                self.assertFalse(get_ticket_plugin(kind).allow_direct_approval(ticket))
                status = adjustment_status(instance, self.alice)
                self.assertTrue(status['pending'])
                self.assertTrue(status['can_adjust'])
                self.assertTrue(status['fields'])
                self.assertEqual(self.save(instance).status_code, 200)
                instance.refresh_from_db()
                ticket.refresh_from_db()
                task.refresh_from_db()
                self.assertEqual(task.state, 'pending')
                self.assertEqual(instance.state, 'running')
                self.assertFalse(instance.context['resources_pending'])
                self.assertEqual(instance.context['resource_revision'], 1)
                self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
                self.assertFalse(TicketSecretAccess.objects.filter(ticket=ticket).exists())
                self.assertEqual(TicketSerializer.get_request_items(ticket)[0]['name'], 'resource_description')
                self.assertNotIn('never-in-ticket', str(instance.context))
                event = instance.events.get(type='resources.adjusted')
                self.assertEqual(event.data['before']['resource_description'], event.data['after']['resource_description'])
                for payload in ({}, {'expected_revision': 0}):
                    self.assertEqual(self.call(task, payload, operation='approve').status_code, 409)
                response = self.call(task, {'expected_revision': 1}, operation='approve')
                self.assertEqual(response.data['state'], 'approved', response.data)
                if kind == 'apply_asset':
                    self.assertEqual(list(AssetPermission.objects.get(pk=ticket.pk).users.all()), [self.applicant])
                else:
                    self.assertTrue(TicketSecretAccess.objects.filter(ticket=ticket, user_id=self.applicant.pk).exists())

    def test_assigned_reviewer_does_not_inherit_resource_permissions(self):
        ticket, instance = self.deferred()
        task = self.task(instance)
        self.assertFalse(adjustment_status(instance, self.alice)['can_adjust'])
        self.assertEqual(self.call(task, operation='resource_options').status_code, 403)
        self.assertEqual(self.save(instance).status_code, 403)
        self.grant_query(org=self.other_org)
        with tmp_to_root_org():
            self.assertEqual(self.save(instance).status_code, 403)
        self.grant_query()
        self.assertEqual(self.call(task, operation='resource_options', user=self.applicant).status_code, 404)
        self.assertEqual(self.call(task, operation='reject').status_code, 200)
        self.assertFalse(TicketSecretAccess.objects.filter(ticket=ticket).exists())
        self.assertEqual(self.call(task, {'expected_revision': 0, 'reason': 'Too late',
                                          'resources': self.resources()}).status_code, 409)

    def test_adjustment_rejects_foreign_accounts_identity_changes_and_stale_saves(self):
        self.create_account()
        self.grant_query()
        ticket, instance = self.deferred()
        with tmp_to_org(self.other_org):
            foreign = Asset.objects.create(name='Foreign', address='192.0.2.90', platform=self.platform)
        for change in ({'asset': str(foreign.pk)}, {'accounts': ['missing']}, {'duration': 86401},
                       {'applicant': str(self.bob.pk)}, {'resource_description': 'replace original'}):
            response = self.save(instance, resources={**self.resources(), **change})
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.save(instance).status_code, 200)
        self.assertEqual(self.save(instance).status_code, 409)
        self.assertEqual(instance.events.filter(type='resources.adjusted').count(), 1)
        self.assertFalse(TicketSecretAccess.objects.filter(ticket=ticket).exists())

    def test_resource_change_restarts_previous_votes_without_erasing_history(self):
        self.create_account()
        self.grant_query()
        self.grant_query(self.bob)
        ticket, instance = self.deferred(definition=approval_definition([self.alice, self.bob], strategy='all'))
        self.assertEqual(self.save(instance).status_code, 200)
        alice = self.task(instance)
        self.assertEqual(self.call(alice, {'expected_revision': 1}, operation='approve').data['state'], 'running')
        bob = self.task(instance, self.bob)
        self.assertEqual(self.save(instance, revision=1, user=self.bob, resources={**self.resources(), 'duration': 120}).status_code, 200)
        alice.refresh_from_db()
        bob.refresh_from_db()
        self.assertEqual(alice.state, 'approved')
        self.assertEqual(bob.state, 'cancelled')
        self.assertEqual(self.call(bob, {'expected_revision': 2}, user=self.bob, operation='approve').status_code, 409)
        self.assertEqual(self.call(self.task(instance, self.bob), {'expected_revision': 2}, user=self.bob, operation='approve').data['state'], 'running')
        self.assertFalse(TicketSecretAccess.objects.filter(ticket=ticket).exists())
        self.assertEqual(self.call(self.task(instance), {'expected_revision': 2}, operation='approve').data['state'], 'approved')
        self.assertEqual(instance.events.filter(type='approval.approved').count(), 3)

    def test_asset_or_owner_change_requires_the_new_owner_to_approve(self):
        original_account = self.create_account()
        self.grant_query()
        replacement = Asset.objects.create(name='Replacement', address='192.0.2.11',
                                           platform=self.platform, owner=self.bob)
        replacement_account = Account.objects.create(asset=replacement, name='root', username='root')
        for kind in ('view_secret', 'apply_asset'):
            for replace_asset in (True, False):
                with self.subTest(kind=kind, replace_asset=replace_asset):
                    Asset.objects.filter(pk=self.asset.pk).update(owner=self.alice)
                    ticket, instance = self.owner_request(kind)
                    old_task = self.task(instance)
                    target = replacement if replace_asset else self.asset
                    if not replace_asset:
                        Asset.objects.filter(pk=self.asset.pk).update(owner=self.bob)
                    values = self.resources(kind)
                    if kind == 'view_secret':
                        values['asset'] = str(target.pk)
                    else:
                        values['apply_assets'] = [str(target.pk)]
                    response = self.save(instance, resources=values)
                    self.assertEqual(response.status_code, 200, response.data)
                    old_task.refresh_from_db()
                    self.assertEqual(old_task.state, 'cancelled')
                    event = instance.events.get(type='resources.adjusted')
                    self.assertTrue(event.data['restarted'])
                    for operation in ('approve', 'reject'):
                        self.assertEqual(self.call(old_task, {'expected_revision': 1},
                                                   operation=operation).status_code, 409)
                    self.assertEqual(self.call(old_task, {
                        'expected_revision': 1, 'reason': 'Stale task', 'resources': values,
                    }).status_code, 409)
                    self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
                    self.assertFalse(TicketSecretAccess.objects.filter(ticket=ticket).exists())
                    new_task = self.task(instance, self.bob)
                    response = self.call(new_task, {'expected_revision': 1}, user=self.bob, operation='approve')
                    self.assertEqual(response.data['state'], 'approved', response.data)
                    if kind == 'apply_asset':
                        self.assertEqual(list(AssetPermission.objects.get(pk=ticket.pk).assets.all()), [target])
                    else:
                        account = replacement_account if replace_asset else original_account
                        self.assertEqual(list(TicketSecretAccess.objects.filter(ticket=ticket)
                                              .values_list('account_id', flat=True)), [account.pk])

    def test_invalid_new_owner_rolls_back_the_entire_adjustment(self):
        self.create_account()
        self.grant_query()
        self.bob.is_active = False
        self.bob.save(update_fields=['is_active'])
        replacement = Asset.objects.create(name='Invalid owner', address='192.0.2.12', platform=self.platform)
        for owner in (None, self.outsider, self.bob):
            with self.subTest(owner=owner):
                Asset.objects.filter(pk=replacement.pk).update(owner=owner)
                ticket, instance = self.owner_request('apply_asset')
                task = self.task(instance)
                before_data, before_context = ticket.request_data, instance.context
                event_count, node_count = instance.events.count(), instance.node_instances.count()
                values = {**self.resources('apply_asset'), 'apply_assets': [str(self.asset.pk), str(replacement.pk)]}
                response = self.save(instance, resources=values)
                self.assertEqual(response.status_code, 400, response.data)
                ticket.refresh_from_db()
                instance.refresh_from_db()
                task.refresh_from_db()
                self.assertEqual(ticket.request_data, before_data)
                self.assertEqual(instance.context, before_context)
                self.assertEqual(instance.events.count(), event_count)
                self.assertEqual(instance.node_instances.count(), node_count)
                self.assertEqual(task.state, 'pending')
                self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_unchanged_asset_owners_preserve_transfer_added_approver_and_deadline(self):
        self.create_account()
        self.grant_query(self.bob)
        _, instance = self.owner_request(allow_transfer=True, allow_add_approver=True, timeout=600)
        task = self.task(instance)
        deadline = task.node_instance.deadline
        self.assertEqual(self.call(task, {'target': str(self.bob.pk)}, operation='transfer').status_code, 200)
        transferred = self.task(instance, self.bob)
        self.assertEqual(self.call(transferred, {'target': str(self.carol.pk)}, user=self.bob,
                                   operation='add_approver').status_code, 200)
        added = self.task(instance, self.carol)
        response = self.save(instance, user=self.bob, resources={**self.resources(), 'duration': 120})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(instance.events.get(type='resources.adjusted').data['restarted'])
        self.assertEqual(self.task(instance, self.bob).pk, transferred.pk)
        self.assertEqual(self.task(instance, self.carol).pk, added.pk)
        self.assertEqual(self.task(instance, self.bob).node_instance.deadline, deadline)
        response = self.call(transferred, {'expected_revision': 1}, user=self.bob, operation='approve')
        self.assertEqual(response.data['state'], 'running')
        response = self.call(added, {'expected_revision': 1}, user=self.carol, operation='approve')
        self.assertEqual(response.data['state'], 'approved')

    def test_description_fallback_is_verified_and_partial_asset_is_preserved(self):
        request = SimpleNamespace(user=self.applicant, query_params={})
        plugin = get_ticket_plugin('view_secret')
        self.assertTrue(resource_availability(plugin, request, self.org.id)['description_allowed'])
        with override_settings(TICKET_APPLY_ASSET_SCOPE='all'):
            self.assertFalse(resource_availability(plugin, request, self.org.id)['description_allowed'])
            invalid = self.serializer(self.payload(resource_description='Skip available choices'))
            self.assertFalse(invalid.is_valid())
            partial = self.serializer(self.payload(asset=str(self.asset.pk), resource_description='Need the database account'))
            self.assertTrue(partial.is_valid(), partial.errors)
            ticket = partial.save()
            instance = submit_ticket(ticket)
            self.assertEqual(instance.context['assets'][0]['id'], str(self.asset.pk))
            self.assertTrue(instance.context['resources_pending'])
            self.create_account()
            no_longer_empty = self.serializer(self.payload(asset=str(self.asset.pk), resource_description='Skip existing accounts'))
            self.assertFalse(no_longer_empty.is_valid())

    @override_settings(TICKET_APPLY_ASSET_SCOPE='all')
    def test_empty_all_accounts_needs_adjustment_but_virtual_accounts_still_work(self):
        for accounts, pending in ((['@ALL'], True), (['@INPUT'], False)):
            with self.subTest(accounts=accounts):
                data = self.payload('apply_asset', **{**self.resources('apply_asset'),
                    'apply_accounts': accounts, 'resource_description': 'Need an account for incident analysis'})
                serializer = self.serializer(data)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                ticket = serializer.save()
                instance = submit_ticket(ticket)
                self.assertEqual(instance.context['resources_pending'], pending)
                self.assertEqual(instance.context['assets'][0]['id'], str(self.asset.pk))
                if pending:
                    self.assertEqual(self.call(self.task(instance), operation='approve').status_code, 409)
                else:
                    self.assertEqual(instance.context['request']['account_selectors'], ['@INPUT'])

    def test_transferred_reviewer_can_save_without_voting_and_deadline_is_preserved(self):
        self.create_account()
        self.grant_query(self.bob)
        _, instance = self.deferred(definition=approval_definition([self.alice], allow_transfer=True, timeout=600))
        task = self.task(instance)
        deadline = task.node_instance.deadline
        response = self.call(task, {'target': str(self.bob.pk)}, operation='transfer')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.save(instance, user=self.bob).status_code, 200)
        replacement = self.task(instance, self.bob)
        self.assertEqual(replacement.node_instance.deadline, deadline)
        self.assertFalse(instance.events.filter(type='approval.approved').exists())

    def test_complete_asset_request_keeps_beneficiary_nodes_dynamic_accounts_and_notice(self):
        self.create_account()
        self.grant_query()
        with override_settings(TICKET_APPLY_ASSET_SCOPE='all'):
            values = self.resources('apply_asset')
            values.update(apply_assets=[], apply_nodes=[str(self.node.pk)], apply_accounts=['@ALL', '@USER'],
                          apply_expire_soon_notice_minutes=10)
            serializer = self.serializer(self.payload('apply_asset', **values))
            self.assertTrue(serializer.is_valid(), serializer.errors)
            ticket = serializer.save()
            instance = submit_ticket(ticket)
        original_users = instance.context['request']['users']
        response = self.save(instance, resources={**values, 'apply_actions': ['connect', 'download']})
        self.assertEqual(response.status_code, 200, response.data)
        instance.refresh_from_db()
        self.assertEqual(instance.context['request']['users'], original_users)
        self.assertEqual(instance.context['nodes'][0]['id'], str(self.node.pk))
        self.assertEqual(instance.context['request']['expire_soon_notice_minutes'], 10)
        self.assertIn('@USER', instance.context['request']['account_selectors'])
        self.assertEqual(self.call(self.task(instance), {'expected_revision': 1}, operation='approve').data['state'], 'approved')
        self.assertEqual(AssetPermission.objects.get(pk=ticket.pk).expire_soon_notice_minutes, 10)
