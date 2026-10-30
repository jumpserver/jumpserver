from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Account
from assets.models import Asset, Protocol
from authentication.models import ConnectionToken
from orgs.utils import tmp_to_org
from perms.const import ActionChoices
from perms.models import AssetPermission
from perms.utils.asset_perm import PermAssetDetailUtil
from perms.utils.permission import AssetPermissionUtil
from tickets.api.plugin import TicketTypeViewSet
from tickets.plugins import get_ticket_plugin
from tickets.serializers.ticket.ticket import TicketSerializer
from tickets.tests import test_plugins as helpers
from tickets.workflow.business import submit_ticket


class FileTransferTests(TestCase):
    setUpTestData = helpers.TicketPluginTests.__dict__['setUpTestData']
    workflow = helpers.TicketPluginTests.workflow
    task = helpers.TicketPluginTests.task
    payload = helpers.TicketPluginTests.payload
    serializer = helpers.TicketPluginTests.serializer

    def setUp(self):
        helpers.TicketPluginTests.setUp(self)
        push = patch('accounts.signal_handlers.push_accounts_if_need.delay')
        push.start()
        self.addCleanup(push.stop)
        self.plugin = get_ticket_plugin('file_transfer')
        self.account = Account.objects.create(asset=self.asset, name='root', username='root', secret='private-secret')
        Protocol.objects.create(asset=self.asset, name='ssh', port=22)
        Protocol.objects.create(asset=self.asset, name='rdp', port=3389)
        self.base = self.grant()

    def grant(self, accounts=None, actions=ActionChoices.connect, protocols=None, user=None):
        grant = AssetPermission.objects.create(
            name=str(uuid4()), accounts=accounts or ['root'], actions=actions, protocols=protocols or ['ssh'],
            date_start=timezone.now() - timedelta(minutes=1), date_expired=timezone.now() + timedelta(days=1),
        )
        grant.assets.add(self.asset)
        grant.users.add(user or self.applicant)
        return grant

    def request_ticket(self, approved=True, **parameters):
        from tickets.models import Ticket
        data = dict(asset=str(self.asset.pk), accounts=['root'], direction='upload', paths=['/tmp/file'], duration=600)
        data.update(parameters)
        # Version 1 is now historical: build persisted fixtures, not new API requests.
        ticket = Ticket.objects.create(type='file_transfer', title='Legacy transfer', applicant=self.applicant,
                                        org_id=self.org.pk, workflow=self.workflow('file_transfer'), request_data=data)
        with patch.object(self.plugin, 'build_context', side_effect=self.legacy_context):
            instance = submit_ticket(ticket)
        if approved:
            self.engine.approve(self.task(instance), self.alice)
        instance.refresh_from_db()
        ticket.refresh_from_db()
        return ticket, instance

    def legacy_context(self, ticket):
        from tickets.plugins.resources import account_context
        from tickets.plugins.file_transfer.permissions import base_access
        context = account_context(ticket)
        access = base_access(ticket.applicant, self.asset)
        context['accounts'] = [a for a in context['accounts'] if a['id'] in access]
        context.update(file_transfer_version=1, actions=[ticket.request_data['direction']],
                       duration=ticket.request_data['duration'],
                       transfer_protocols={a['id']: access[a['id']]['protocols'] for a in context['accounts']})
        return context

    def actions(self, account=None, protocol='ssh', user=None):
        permed = ConnectionToken.get_user_permed_account(user or self.applicant, self.asset,
                                                        str((account or self.account).pk), protocol)
        return permed.actions if permed else 0

    def test_final_approval_grants_frozen_direction_and_is_idempotent(self):
        ticket, instance = self.request_ticket(approved=False)
        self.assertEqual(self.plugin.get_transfer_status(ticket)['state'], 'pending')
        self.assertEqual(self.actions(), ActionChoices.connect)
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
        ticket.request_data.update(direction='download', accounts=['someone-else'], duration=86400)
        ticket.save(update_fields=['request_data'])
        self.engine.approve(self.task(instance), self.alice)
        instance.refresh_from_db()
        ticket.refresh_from_db()
        grant = AssetPermission.objects.get(pk=ticket.pk)
        self.assertEqual(grant.actions, ActionChoices.upload)
        self.assertEqual(grant.accounts, ['root'])
        self.assertEqual(grant.protocols, ['ssh'])
        self.assertEqual(grant.date_expired, instance.date_finished + timedelta(seconds=600))
        self.assertEqual(self.actions(), ActionChoices.connect | ActionChoices.upload)
        self.assertEqual(self.actions(protocol='rdp'), 0)
        self.assertEqual(self.actions(user=self.bob), 0)
        self.assertIsNone(self.plugin.on_approved(instance, ticket))
        grant.refresh_from_db()
        self.assertEqual(grant.date_expired, instance.date_finished + timedelta(seconds=600))
        self.assertEqual(instance.events.filter(type='action.executed').count(), 1)
        self.assertNotIn('private-secret', str(instance.context))
        self.assertNotIn(grant.pk, AssetPermissionUtil().get_permissions_for_user(self.applicant, flat=True))

    def test_download_does_not_grant_upload_delete_or_clipboard(self):
        self.request_ticket(direction='download')
        self.assertEqual(self.actions(), ActionChoices.connect | ActionChoices.download)

    def test_exclusions_still_override_ticket_grants(self):
        self.grant(accounts=['!root'], actions=ActionChoices.upload)
        ticket, _ = self.request_ticket()
        self.assertEqual(self.actions(), ActionChoices.connect)
        self.assertEqual(self.plugin.get_transfer_status(ticket)['state'], 'unavailable')

    def test_expiry_and_revocation_do_not_remove_independent_permissions(self):
        ticket, _ = self.request_ticket()
        self.grant(actions=ActionChoices.connect | ActionChoices.download)
        AssetPermission.objects.filter(pk=ticket.pk).update(date_expired=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.actions(), ActionChoices.connect | ActionChoices.download)
        self.assertEqual(self.plugin.get_transfer_status(ticket)['state'], 'expired')

    def test_missing_base_access_cannot_be_replaced_by_transfer_grant(self):
        ticket, _ = self.request_ticket()
        self.base.is_active = False
        self.base.save(update_fields=['is_active'])
        self.assertEqual(self.actions(), 0)
        self.assertEqual(self.plugin.get_transfer_status(ticket)['state'], 'unavailable')
        self.assertFalse(self.serializer(self.payload('file_transfer', asset=str(self.asset.pk), accounts=['root'],
                                                      direction='upload', paths=['/tmp/file'])).is_valid())

    def test_new_permissions_do_not_expand_frozen_protocols(self):
        self.request_ticket()
        self.grant(protocols=['rdp'])
        self.assertEqual(self.actions(protocol='rdp'), ActionChoices.connect)
        self.assertEqual(self.actions(), ActionChoices.connect | ActionChoices.upload)

    def test_each_account_keeps_its_own_protocol_scope(self):
        other = Account.objects.create(asset=self.asset, name='operator', username='operator')
        self.grant(accounts=['operator'], protocols=['rdp'])
        self.request_ticket(accounts=['root', 'operator'])
        self.assertEqual(self.actions(protocol='rdp'), 0)
        self.assertEqual(self.actions(other, 'ssh'), 0)
        self.assertEqual(self.actions(other, 'rdp'), ActionChoices.connect | ActionChoices.upload)

    def test_account_identity_and_membership_are_checked_on_each_connection(self):
        ticket, _ = self.request_ticket()
        self.account.delete()
        self.account = Account.objects.create(asset=self.asset, name='root', username='root')
        self.assertEqual(self.actions(), ActionChoices.connect)
        self.assertEqual(self.plugin.get_transfer_status(ticket)['state'], 'unavailable')

    def test_unrelated_asset_cannot_receive_the_ticket_actions(self):
        self.request_ticket()
        other = Asset.objects.create(name='Other', address='192.0.2.11', platform=self.platform)
        account = Account.objects.create(asset=other, name='root', username='root')
        Protocol.objects.create(asset=other, name='ssh', port=22)
        self.base.assets.add(other)
        permed = ConnectionToken.get_user_permed_account(self.applicant, other, str(account.pk), 'ssh')
        self.assertEqual(permed.actions, ActionChoices.connect)

    def test_options_only_include_active_accounts_with_existing_access(self):
        Account.objects.create(asset=self.asset, name='ungranted', username='ungranted')
        Account.objects.create(asset=self.asset, name='disabled', username='disabled', is_active=False)
        request = APIRequestFactory().get('/', {'org_id': self.org.pk, 'asset': self.asset.pk})
        force_authenticate(request, self.applicant)
        response = TicketTypeViewSet.as_view({'get': 'resource_options'})(request, pk='file_transfer')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, ['root'])
        with tmp_to_org(self.other_org):
            other = Asset.objects.create(name='Other org', address='192.0.2.20', platform=self.platform)
        data = self.payload('file_transfer', asset=str(other.pk), accounts=['root'], direction='upload', paths=['/tmp'])
        self.assertFalse(self.serializer(data).is_valid())

    def test_validation_rejects_missing_access_and_forged_execution_parameters(self):
        for changes in ({'accounts': ['unknown']}, {'duration': 0}, {'duration': 86401},
                        {'direction': 'delete'}, {'file_transfer_version': 1}, {'protocols': ['all']}):
            data = dict(asset=str(self.asset.pk), accounts=['root'], direction='upload', paths=['/tmp'])
            self.assertFalse(self.serializer(self.payload('file_transfer', **{**data, **changes})).is_valid())
        self.base.delete()
        self.assertFalse(self.serializer(self.payload('file_transfer', asset=str(self.asset.pk), accounts=['root'],
                                                      direction='upload', paths=['/tmp'])).is_valid())

    def test_changed_base_access_before_final_approval_creates_no_grant(self):
        ticket, instance = self.request_ticket(approved=False)
        self.base.delete()
        self.engine.approve(self.task(instance), self.alice)
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'error')
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_reject_and_withdraw_do_not_grant_access(self):
        ticket, instance = self.request_ticket(approved=False)
        self.engine.reject(self.task(instance), self.alice)
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
        ticket, instance = self.request_ticket(approved=False)
        self.engine.cancel(instance, self.applicant)
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_historical_pending_and_completed_tickets_stay_approval_only(self):
        for approved in (False, True):
            original = self.legacy_context
            def legacy_context(ticket):
                context = original(ticket)
                context.pop('file_transfer_version')
                return context
            with patch.object(self, 'legacy_context', side_effect=legacy_context):
                ticket, instance = self.request_ticket(approved=False)
            if approved:
                self.engine.approve(self.task(instance), self.alice)
            ticket.refresh_from_db()
            self.assertEqual(TicketSerializer(ticket).data['execution_mode'], 'approval_only')
            self.assertEqual(self.plugin.get_transfer_status(ticket), {'state': 'approval_only'})
            self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())

    def test_status_is_only_exposed_on_detail(self):
        ticket, _ = self.request_ticket()
        self.assertIsNone(TicketSerializer(ticket).data['result'])
        context = {'view': SimpleNamespace(action='retrieve'), 'request': SimpleNamespace(user=self.alice)}
        data = TicketSerializer(ticket, context=context).data
        self.assertEqual(data['execution_mode'], 'automatic')
        self.assertEqual(data['result']['state'], 'available')
        self.assertEqual(data['result']['accounts'], ['root'])
        self.assertEqual(data['result']['actions'], [])

    def test_new_token_exchange_recalculates_expired_transfer_permission(self):
        ticket, _ = self.request_ticket()
        token = ConnectionToken.objects.create(user=self.applicant, asset=self.asset,
                                               account=str(self.account.pk), protocol='ssh', connect_method='web_cli')
        self.assertEqual(token.actions, ActionChoices.connect | ActionChoices.upload)
        AssetPermission.objects.filter(pk=ticket.pk).update(date_expired=timezone.now() - timedelta(seconds=1))
        exchanged = ConnectionToken.objects.get(pk=token.pk)
        self.assertEqual(exchanged.actions, ActionChoices.connect)
        self.assertEqual(exchanged.expire_at, self.base.date_expired.timestamp())

    def test_inactive_account_asset_or_applicant_does_not_receive_ticket_actions(self):
        ticket, _ = self.request_ticket()
        for obj in (self.account, self.asset, self.applicant):
            type(obj).objects.filter(pk=obj.pk).update(is_active=False)
            self.asset.refresh_from_db()
            self.assertFalse(self.actions() & ActionChoices.upload)
            self.assertEqual(self.plugin.get_transfer_status(ticket)['state'], 'unavailable')
            type(obj).objects.filter(pk=obj.pk).update(is_active=True)
            self.asset.refresh_from_db()

    def test_inactive_account_with_same_username_is_not_in_the_frozen_targets(self):
        disabled = Account.objects.create(asset=self.asset, name='old root', username='root', secret_type='ssh_key', is_active=False)
        ticket, instance = self.request_ticket()
        self.assertEqual([a['id'] for a in instance.context['accounts']], [str(self.account.pk)])
        self.assertNotIn(str(disabled.pk), instance.context['transfer_protocols'])
        self.assertEqual(self.plugin.get_transfer_status(ticket)['state'], 'available')

    def test_approval_transaction_rollback_does_not_leave_a_grant(self):
        ticket, instance = self.request_ticket(approved=False)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.engine.approve(self.task(instance), self.alice)
                self.assertTrue(AssetPermission.objects.filter(pk=ticket.pk).exists())
                raise RuntimeError('rollback')
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
        ticket.refresh_from_db()
        self.assertEqual(ticket.state, 'pending')
