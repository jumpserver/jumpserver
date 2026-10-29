from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase, override_settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.exceptions import PermissionDenied

from accounts.models import Account
from assets.models import Asset
from orgs.utils import tmp_to_org
from perms.models import AssetPermission
from perms.notifications import AssetPermissionWillExpireSoonUserMsg, PermedAssetsWillExpireUserMsg
from rbac.models import Permission, Role, RoleBinding
from tickets.api.ticket import TicketViewSet
from tickets.models import TicketBeneficiary
from tickets.plugins.apply_asset.reapply import reapply_kind
from tickets.tests import test_plugins, test_workflow
from tickets.workflow.business import submit_ticket
from tickets.workflow.approvers import available_users
from tickets.workflow.publication import publish_workflow


@override_settings(TICKET_APPLY_ASSET_SCOPE='all', TICKET_AUTHORIZE_DEFAULT_TIME=2,
                   TICKET_AUTHORIZE_DEFAULT_TIME_UNIT='hour')
class AssetReapplyTests(TestCase):
    setUpTestData = test_workflow.WorkflowTests.__dict__['setUpTestData']
    setUp = test_plugins.TicketPluginTests.setUp
    workflow = test_plugins.TicketPluginTests.workflow
    ticket = test_plugins.TicketPluginTests.ticket
    task = test_plugins.TicketPluginTests.task
    serializer = test_plugins.TicketPluginTests.serializer

    def source(self, approved=True):
        Account.objects.create(asset=self.asset, name='root', username='root')
        ticket = self.ticket()
        ticket.request_data.update(apply_assets=[], apply_nodes=[str(self.node.pk)])
        ticket.save(update_fields=['request_data'])
        instance = submit_ticket(ticket)
        if approved:
            self.engine.approve(self.task(instance), self.alice)
        else:
            self.engine.reject(self.task(instance), self.alice)
        ticket.refresh_from_db()
        return ticket

    def prefill(self, ticket, user=None):
        request = APIRequestFactory().get('/api/v1/tickets/tickets/actions/reapply_asset/')
        force_authenticate(request, user or self.applicant)
        with transaction.atomic():
            return TicketViewSet.as_view({'get': 'perform_action'}, **TicketViewSet.perform_action.kwargs)(
                request, pk=str(ticket.pk), action_name='reapply_asset')

    def payload(self, prefill):
        return {key: prefill[key] for key in ('title', 'comment', 'org_id', 'workflow_id', 'request_data')} | {
            'type': 'apply_asset', 'source_ticket_id': prefill['source_ticket']['id'],
        }

    def listing(self, user, **params):
        role, _ = Role.objects.get_or_create(name='Reapply list access', scope='system')
        role.permissions.add(Permission.objects.get(codename='view_ticket', content_type__model='ticket'))
        RoleBinding.objects_raw.get_or_create(user=user, role=role, scope='system')
        user.expire_rbac_perms_cache()
        user = type(user).objects.get(pk=user.pk)
        request = APIRequestFactory().get('/api/v1/tickets/tickets/', {'limit': 20, 'state': 'all', **params})
        force_authenticate(request, user)
        with transaction.atomic():
            response = TicketViewSet.as_view({'get': 'list'})(request)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data['results']

    def test_list_actions_follow_ticket_state_and_current_user_relationship(self):
        source = self.source()
        TicketBeneficiary.objects.create(ticket=source, user=self.carol)
        source.cc_users.add(self.bob)
        for user, action in ((self.applicant, 'reapply'), (self.carol, None),
                             (self.alice, None), (self.bob, None)):
            with self.subTest(user=user.username):
                rows = self.listing(user, id=str(source.pk))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['reapply_action'], action)
        for state in ('rejected', 'closed', 'expired', 'error', 'pending'):
            source.state = state
            source.save(update_fields=['state'])
            rows = self.listing(self.applicant, id=str(source.pk))
            self.assertEqual(rows[0]['reapply_action'], 'reapply')

    def test_list_membership_checks_are_shared_only_within_one_request(self):
        source = self.source()
        second = self.ticket(workflow=source.workflow)
        second.state = 'rejected'
        second.save(update_fields=['state'])
        with patch('tickets.plugins.reapply.available_users', wraps=available_users) as members:
            rows = self.listing(self.applicant)
            self.assertEqual({row['reapply_action'] for row in rows}, {'reapply'})
            members.assert_called_once_with(self.org.id)
        with patch('tickets.plugins.reapply.available_users',
                   return_value=type(self.applicant).objects.none()):
            self.assertTrue(all(row['reapply_action'] is None for row in self.listing(self.applicant)))

    def test_renewal_freezes_approved_scope_and_requires_new_approval_on_latest_version(self):
        source = self.source()
        grant = AssetPermission.objects.get(pk=source.pk)
        original_expiry = grant.date_expired
        extra = Asset.objects.create(name='Added later', address='192.0.2.11', platform=self.platform)
        extra.nodes.add(self.node)
        Account.objects.create(asset=extra, name='new', username='new')
        data = self.prefill(source).data
        self.assertEqual(data['source_ticket']['kind'], 'renew')
        self.assertEqual(data['request_data']['apply_assets'], [str(self.asset.pk)])
        self.assertEqual(data['request_data']['apply_nodes'], [])
        self.assertEqual(data['request_data']['apply_accounts'], ['root'])
        self.assertEqual(parse_datetime(data['request_data']['apply_date_start']), original_expiry)
        self.assertEqual(parse_datetime(data['request_data']['apply_date_expired']), original_expiry + timedelta(hours=2))
        workflow = source.workflow
        version = publish_workflow(workflow, test_workflow.approval_definition([self.bob]), expected_version=1)
        serializer = self.serializer(self.payload(data))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        new = serializer.save()
        instance = submit_ticket(new)
        self.assertEqual(instance.version_id, version.pk)
        self.assertNotEqual(new.pk, source.pk)
        self.assertFalse(AssetPermission.objects.filter(pk=new.pk).exists())
        self.assertEqual(new.meta['source_ticket']['id'], str(source.pk))
        self.engine.approve(self.task(instance, self.bob), self.bob)
        self.assertEqual(list(AssetPermission.objects.get(pk=new.pk).assets.all()), [self.asset])
        grant.refresh_from_db()
        self.assertEqual(grant.date_expired, original_expiry)

    def test_rejected_and_pending_requests_can_be_reapplied(self):
        source = self.source(approved=False)
        data = self.prefill(source).data
        self.assertEqual(data['source_ticket']['kind'], 'reapply')
        self.assertLess(abs((parse_datetime(data['request_data']['apply_date_start']) - timezone.now()).total_seconds()), 5)
        source.state = 'pending'
        source.save(update_fields=['state'])
        self.assertEqual(reapply_kind(source, self.applicant), 'reapply')
        self.assertEqual(self.prefill(source).status_code, 200)

    def test_actor_and_organization_checks_apply_to_prefill_and_submission(self):
        source = self.source()
        self.assertEqual(self.prefill(source, self.alice).status_code, 403)
        source.cc_users.add(self.carol)
        self.assertEqual(self.prefill(source, self.carol).status_code, 403)
        self.assertIsNone(reapply_kind(source, self.outsider))
        data = self.payload(self.prefill(source).data)
        data['source_ticket_id'] = str(uuid4())
        with self.assertRaises(PermissionDenied) as error:
            self.serializer(data).is_valid(raise_exception=True)
        self.assertEqual(error.exception.status_code, 403)
        with tmp_to_org(self.other_org):
            self.assertEqual(self.prefill(source).status_code, 404)

    def test_beneficiary_can_renew_for_self_but_cannot_impersonate_original_applicant(self):
        source = self.source()
        TicketBeneficiary.objects.create(ticket=source, user=self.carol)
        source.request_data['apply_users'] = [str(self.carol.pk)]
        source.save(update_fields=['request_data'])
        data = self.prefill(source, self.carol).data
        self.assertEqual(data['request_data']['apply_users'], [str(self.carol.pk)])
        serializer = self.serializer(self.payload(data), self.carol)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.save().applicant_id, self.carol.pk)
        data['request_data']['apply_users'] = [str(self.applicant.pk)]
        with self.assertRaises(PermissionDenied):
            self.serializer(self.payload(data), self.carol).is_valid(raise_exception=True)

    def test_invalid_resources_are_reported_and_stale_prefill_is_revalidated(self):
        source = self.source()
        data = self.prefill(source).data
        self.asset.is_active = False
        self.asset.save(update_fields=['is_active'])
        prefill = self.prefill(source).data
        self.assertEqual(prefill['request_data']['apply_assets'], [])
        self.assertEqual(prefill['warnings']['assets'], 1)
        self.assertIn('root', prefill['warnings']['accounts'])
        serializer = self.serializer(self.payload(data))
        self.assertFalse(serializer.is_valid())
        self.assertIn('apply_assets', serializer.errors)

    def test_expired_grant_defaults_to_now_and_does_not_copy_an_old_deadline(self):
        source = self.source()
        AssetPermission.objects.filter(pk=source.pk).update(date_expired=timezone.now() - timedelta(days=1))
        data = self.prefill(source).data['request_data']
        self.assertLess(abs((parse_datetime(data['apply_date_start']) - timezone.now()).total_seconds()), 5)
        self.assertGreater(parse_datetime(data['apply_date_expired']), timezone.now())

    def test_current_application_scope_is_not_bypassed_by_a_source_ticket(self):
        source = self.source(approved=False)
        data = self.prefill(source).data
        with override_settings(TICKET_APPLY_ASSET_SCOPE='permed_valid'):
            self.assertEqual(self.prefill(source).data['request_data']['apply_assets'], [])
            serializer = self.serializer(self.payload(data))
            self.assertFalse(serializer.is_valid())

    def test_both_expiration_notifications_link_only_to_eligible_source_tickets(self):
        source = self.source()
        grant = AssetPermission.objects.get(pk=source.pk)
        for user, has_link in ((self.applicant, True), (self.alice, False)):
            for message in (AssetPermissionWillExpireSoonUserMsg(user, grant),
                            PermedAssetsWillExpireUserMsg(user, [self.asset], 1, permissions=[grant])):
                html = message.get_html_msg()['message']
                self.assertEqual(f'source_ticket={source.pk}' in html, has_link)
                if has_link:
                    self.assertIn(f'oid={self.org.pk}', html)
        with patch('perms.tasks.PermedAssetsWillExpireUserMsg') as notification, \
                patch('perms.tasks.AssetPermsWillExpireForOrgAdminMsg'):
            from perms.tasks import check_asset_permission_will_expired
            check_asset_permission_will_expired()
            self.assertTrue(notification.called)
            self.assertTrue(any(grant in call.kwargs['permissions'] for call in notification.call_args_list))
