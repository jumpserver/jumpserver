from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from orgs.utils import tmp_to_org
from rbac.models import Permission, Role, RoleBinding
from terminal.models import Session
from tickets.api.ticket import TicketViewSet
from tickets.models import Ticket, WorkflowInstance
from tickets.plugins import get_ticket_plugin
from tickets.plugins.reapply import can_reapply
from tickets.tests import test_plugins, test_file_transfer
from tickets.workflow.business import submit_ticket
from tickets.workflow.publication import publish_workflow
from tickets.tests.test_workflow import approval_definition


class ManualReapplyTests(TestCase):
    setUpTestData = test_plugins.TicketPluginTests.__dict__['setUpTestData']
    workflow = test_plugins.TicketPluginTests.workflow
    serializer = test_plugins.TicketPluginTests.serializer
    grant = test_file_transfer.FileTransferTests.grant

    def setUp(self):
        test_file_transfer.FileTransferTests.setUp(self)
        role = Role.objects.create(name='Manual reapply', scope='system')
        role.permissions.add(Permission.objects.get(codename='view_ticket', content_type__model='ticket'))
        RoleBinding.objects_raw.create(user=self.applicant, role=role, scope='system')
        self.applicant.expire_rbac_perms_cache()
        self.applicant = type(self.applicant).objects.get(pk=self.applicant.pk)
        self.session = Session.objects.create(user_id=str(self.applicant.pk), user='Applicant',
                                             asset_id=str(self.asset.pk), asset='Test host', account='root',
                                             has_replay=True, is_finished=True)

    def source(self, kind='file_transfer', **data):
        values = {'asset': str(self.asset.pk), 'accounts': ['root']}
        if kind == 'file_transfer':
            values.update(direction='download', paths=['/tmp/report.txt'], duration=600)
        elif kind == 'download_replay':
            values = {'session': str(self.session.pk), 'duration': 600}
        elif kind == 'view_secret':
            values['duration'] = 600
        values.update(data)
        return Ticket.objects.create(type=kind, title='Reuse request', applicant=self.applicant,
                                     org_id=self.org.id, workflow=self.workflow(kind), request_data=values)

    def prefill(self, source, user=None):
        request = APIRequestFactory().get('/api/v1/tickets/tickets/actions/reapply/')
        force_authenticate(request, user or self.applicant)
        with transaction.atomic():
            return TicketViewSet.as_view({'get': 'perform_action'}, **TicketViewSet.perform_action.kwargs)(
                request, pk=str(source.pk), action_name='reapply')

    def payload(self, data):
        return {key: data[key] for key in ('title', 'comment', 'org_id', 'workflow_id', 'request_data', 'type')} | {
            'source_ticket_id': data['source_ticket']['id'],
        }

    def test_all_manual_types_and_states_share_applicant_only_eligibility(self):
        for kind in ('apply_asset', 'view_secret', 'change_secret', 'file_transfer', 'download_replay'):
            source = self.source(kind)
            for state in ('pending', 'approved', 'rejected', 'closed', 'expired', 'error'):
                source.state = state
                self.assertTrue(can_reapply(source, self.applicant), (kind, state))
                self.assertFalse(can_reapply(source, self.alice))
        with patch.object(self.applicant, 'has_perm', return_value=False):
            self.assertFalse(can_reapply(source, self.applicant))

    def test_automatic_reviews_have_neither_button_nor_action(self):
        for kind in ('login_confirm', 'login_asset_confirm', 'command_confirm'):
            source = self.source(kind)
            self.assertFalse(can_reapply(source, self.applicant))
            self.assertEqual(self.prefill(source).status_code, 404)

    def test_prefill_is_read_only_and_copies_only_current_request_fields(self):
        source = self.source(files=[str(uuid4())], secret='not-an-input', expires_at='old')
        original = deepcopy(source.request_data)
        count = Ticket.objects.count()
        response = self.prefill(source)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.data['request_data'], {
            'asset': str(self.asset.pk), 'accounts': ['root'], 'direction': 'download',
            'paths': ['/tmp/report.txt'], 'duration': 600,
        })
        self.assertEqual(self.asset.name, response.data['resources']['asset'][0]['name'])
        self.assertEqual(Ticket.objects.count(), count)
        source.refresh_from_db()
        self.assertEqual(source.request_data, original)

    def test_upload_requires_new_files_and_submission_does_not_reuse_execution(self):
        source = self.source(direction='upload', paths=[], target_directory='/tmp', files=[str(uuid4())])
        data = self.prefill(source).data
        self.assertNotIn('files', data['request_data'])
        serializer = self.serializer(self.payload(data))
        self.assertFalse(serializer.is_valid())
        self.assertIn('request_data', serializer.errors)

    def test_reapply_creates_new_pending_ticket_using_latest_workflow(self):
        source = self.source()
        data = self.prefill(source).data
        version = publish_workflow(source.workflow, approval_definition([self.bob]), expected_version=1)
        request = APIRequestFactory().post('/api/v1/tickets/tickets/open/', self.payload(data), format='json')
        force_authenticate(request, self.applicant)
        response = TicketViewSet.as_view({'post': 'open'}, **TicketViewSet.open.kwargs)(request)
        self.assertEqual(response.status_code, 201, response.data)
        new = Ticket.objects.get(pk=response.data['id'])
        instance = new.workflow_instance
        self.assertNotEqual(new.pk, source.pk)
        self.assertEqual(instance.version_id, version.pk)
        self.assertEqual(instance.state, 'running')
        self.assertEqual(new.state, 'pending')
        self.assertEqual(new.meta['source_ticket']['id'], str(source.pk))
        self.assertEqual(new.meta['source_ticket']['kind'], 'reapply')
        self.assertFalse(WorkflowInstance.objects.filter(ticket=source).exists())

    def test_adjusted_snapshot_is_reused_instead_of_superseded_request_fields(self):
        source = self.source()
        submit_ticket(source)
        source.request_data['paths'] = ['/tmp/superseded-request.txt']
        source.save(update_fields=['request_data'])
        source.refresh_from_db()
        self.assertEqual(self.prefill(source).data['request_data']['paths'], ['/tmp/report.txt'])

    def test_deleted_resources_and_recording_are_removed_and_stale_submission_is_rejected(self):
        source = self.source()
        payload = self.payload(self.prefill(source).data)
        self.account.delete()
        data = self.prefill(source).data
        self.assertEqual(data['request_data']['accounts'], [])
        self.assertIn('accounts', data['warnings'])
        self.assertFalse(self.serializer(payload).is_valid())
        self.asset.is_active = False
        self.asset.save(update_fields=['is_active'])
        data = self.prefill(source).data
        self.assertNotIn('asset', data['request_data'])
        source = self.source('download_replay')
        self.assertIn('session', self.prefill(source).data['resources'])
        self.session.has_replay = False
        self.session.save(update_fields=['has_replay'])
        self.assertNotIn('session', self.prefill(source).data['request_data'])

    def test_prefill_and_submission_enforce_actor_type_and_organization(self):
        source = self.source()
        source.cc_users.add(self.alice)
        self.assertEqual(self.prefill(source, self.alice).status_code, 403)
        with tmp_to_org(self.other_org):
            self.assertEqual(self.prefill(source).status_code, 404)
        payload = self.payload(self.prefill(source).data)
        payload['source_ticket_id'] = str(self.source('view_secret').pk)
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            self.serializer(payload).is_valid(raise_exception=True)

    def test_view_secret_change_secret_and_asset_prefill(self):
        for kind in ('view_secret', 'change_secret'):
            source = self.source(kind)
            with patch('tickets.plugins.change_secret.serializer.RequestSerializer.validate_asset', return_value=self.asset.pk):
                response = self.prefill(source)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['type'], kind)
        source = test_plugins.TicketPluginTests.ticket(self)
        source.state = 'approved'
        source.save(update_fields=['state'])
        data = self.prefill(source).data
        self.assertEqual(data['source_ticket']['kind'], 'reapply')
        self.assertEqual(data['assets'], [{'id': str(self.asset.pk), 'name': self.asset.name,
                                          'address': self.asset.address}])
        from django.utils.dateparse import parse_datetime
        self.assertLess(abs((parse_datetime(data['request_data']['apply_date_start']) - timezone.now()).total_seconds()), 5)
