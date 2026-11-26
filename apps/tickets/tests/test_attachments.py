import io
import json
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from orgs.utils import current_org, tmp_to_org
from rbac.models import Permission, Role, RoleBinding
from settings.serializers.feature import TicketSettingSerializer
from tickets.api.ticket import TicketViewSet
from tickets.attachments import MAX_FILE_SIZE, cleanup_attachments, save_attachment
from tickets.models import Ticket, TicketAttachment, TicketBeneficiary
from tickets.serializers.ticket.ticket import TicketSerializer
from tickets.tests import test_plugins as helpers
from users.models import User


@override_settings(TICKET_ATTACHMENT_RETENTION_DAYS=30)
class TicketAttachmentTests(TestCase):
    setUpTestData = helpers.TicketPluginTests.__dict__['setUpTestData']
    workflow = helpers.TicketPluginTests.workflow
    payload = helpers.TicketPluginTests.payload

    def setUp(self):
        helpers.TicketPluginTests.setUp(self)
        role = Role.objects.create(name='Attachment applicants', scope='system')
        role.permissions.add(Permission.objects.get(content_type__app_label='tickets', codename='view_ticket'))
        RoleBinding.objects_raw.bulk_create([
            RoleBinding(user=user, role=role, scope='system')
            for user in (self.applicant, self.alice, self.bob, self.carol, self.outsider)
        ])
        for user in (self.applicant, self.alice, self.bob, self.carol, self.outsider):
            user.expire_rbac_perms_cache()
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        override = override_settings(SHARE_DIR=self.directory.name)
        override.enable()
        self.addCleanup(override.disable)

    @staticmethod
    def file(name='proof.pdf', content=b'%PDF-1.4\nproof'):
        return SimpleUploadedFile(name, content)

    def image(self):
        buffer = io.BytesIO()
        Image.new('RGB', (2, 2)).save(buffer, format='PNG')
        return self.file('proof.png', buffer.getvalue())

    def open(self, files=(), *, user=None, payload=None, multipart=True):
        payload = payload or self.payload('apply_asset',
            apply_users=[str(self.applicant.pk)], apply_assets=[str(self.asset.pk)],
            apply_accounts=['root'], apply_actions=['connect'],
            apply_date_start=timezone.now().isoformat(),
            apply_date_expired=(timezone.now() + timedelta(hours=1)).isoformat(),
        )
        if multipart:
            payload = {**payload, 'request_data': json.dumps(payload['request_data']), 'attachments': list(files)}
        request = APIRequestFactory().post('/', payload, format='multipart' if multipart else 'json')
        force_authenticate(request, user or self.applicant)
        with tmp_to_org(current_org.id), transaction.atomic():
            return TicketViewSet.as_view({'post': 'open'}, **TicketViewSet.open.kwargs)(request)

    def download(self, ticket, record, user=None, *, preview=False):
        request = APIRequestFactory().get('/', {'preview': '1'} if preview else {})
        if user is not False:
            force_authenticate(request, user or self.applicant)
        with tmp_to_org(current_org.id), transaction.atomic():
            return TicketViewSet.as_view({'get': 'attachment'}, **TicketViewSet.attachment.kwargs)(
                request, pk=str(ticket.pk), attachment_id=str(record.pk),
            )

    def created(self, files=None):
        with tmp_to_org(self.org):
            response = self.open(files if files is not None else [self.file()])
            self.assertEqual(response.status_code, 201, response.data)
            ticket = Ticket.objects.get(pk=response.data['id'])
            return ticket, ticket.attachments.first()

    def test_multipart_submission_keeps_original_files_and_metadata(self):
        image = self.image()
        original = image.read()
        image.seek(0)
        ticket, record = self.created([image, self.file('证明材料.docx')])
        records = list(ticket.attachments.all())
        self.assertEqual(len(records), 2)
        record = next(r for r in records if r.name.endswith('.png'))
        self.assertEqual(record.path.read_bytes(), original)
        self.assertEqual(record.content_type, 'image/png')
        self.assertEqual(record.expires_at, record.date_created + timedelta(days=30))
        self.assertEqual(record.org_id, str(self.org.pk))
        self.assertEqual(TicketSerializer(ticket).data['attachments'][0]['expired'], False)
        response = self.download(ticket, record, preview=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
        self.assertEqual(b''.join(response.streaming_content), original)
        response.close()
        response = self.download(ticket, records[1], preview=True)
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['Cache-Control'], 'no-store')
        response.close()

    def test_existing_json_submission_and_generic_plugin_still_work(self):
        self.assertEqual(self.open(multipart=False).status_code, 201)
        from terminal.models import Session
        session = Session.objects.create(user_id=str(self.applicant.pk), asset_id=str(self.asset.pk),
                                         account='root', has_replay=True, is_finished=True)
        payload = self.payload('download_replay', session=str(session.pk), duration=600)
        response = self.open([self.file()], payload=payload)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data['attachments']), 1)

    def test_rejects_invalid_files_before_creating_a_ticket(self):
        for files in ([self.file('payload.html')], [self.file('fake.png')], [self.file(content=b'')],
                      [self.file(content=b'x' * (MAX_FILE_SIZE + 1))],
                      [self.file(f'{i}.pdf') for i in range(6)]):
            with self.subTest(names=[f.name for f in files]):
                response = self.open(files)
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn('attachments', response.data)
        self.assertFalse(Ticket.objects.exists())
        self.assertFalse(TicketAttachment.objects.exists())
        self.assertFalse(list(Path(self.directory.name).rglob('*')))

    def test_download_permissions_follow_ticket_visibility(self):
        ticket, record = self.created()
        for user in (self.applicant, self.alice):
            response = self.download(ticket, record, user)
            self.assertEqual(response.status_code, 200)
            response.close()
        self.assertEqual(self.download(ticket, record, self.bob).status_code, 404)
        ticket.cc_users.add(self.bob)
        response = self.download(ticket, record, self.bob)
        self.assertEqual(response.status_code, 200)
        response.close()
        TicketBeneficiary.objects.create(ticket=ticket, user=self.carol)
        response = self.download(ticket, record, self.carol)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertEqual(self.download(ticket, record, self.outsider).status_code, 404)
        self.assertIn(self.download(ticket, record, False).status_code, (401, 403))
        other_ticket, _ = self.created()
        self.assertEqual(self.download(other_ticket, record).status_code, 404)

    def test_only_current_approver_can_download_with_exhausted_file_quota(self):
        from common.drf.throttling import FileTransferThrottle

        ticket, record = self.created()
        ticket.cc_users.add(self.bob)
        with patch.object(FileTransferThrottle, 'allow_request', return_value=False) as check_quota, \
                patch.object(FileTransferThrottle, 'wait', return_value=60):
            response = self.download(ticket, record, self.alice)
            self.assertEqual(response.status_code, 200)
            response.close()
            check_quota.assert_not_called()
            for user in (self.applicant, self.bob):
                response = self.download(ticket, record, user)
                self.assertEqual(response.status_code, 429)
                self.assertEqual(response['Retry-After'], '60')
            ticket.reject(self.alice)
            self.assertEqual(self.download(ticket, record, self.alice).status_code, 429)

    def test_audit_access_is_scoped_to_the_audited_organization(self):
        ticket, record = self.created()
        role = Role.objects.create(name='Attachment auditor', scope='org')
        role.permissions.add(Permission.objects.get(content_type__app_label='audits', codename='view_ticketaudit'))
        RoleBinding.objects_raw.create(user=self.bob, role=role, org=self.org, scope='org')
        self.bob.expire_rbac_perms_cache()
        response = self.download(ticket, record, User.objects.get(pk=self.bob.pk))
        self.assertEqual(response.status_code, 200)
        response.close()
        with tmp_to_org(self.other_org):
            self.assertIn(self.download(ticket, record, User.objects.get(pk=self.bob.pk)).status_code, (403, 404))

    def test_write_failure_rolls_back_ticket_and_removes_all_written_files(self):
        def fail_second(record, upload):
            save_attachment(record, upload)
            if record.name == 'second.pdf':
                raise OSError('disk full')
        with patch('tickets.attachments.save_attachment', side_effect=fail_second):
            with self.assertRaisesMessage(OSError, 'disk full'):
                self.open([self.file(), self.file('second.pdf')])
        self.assertFalse(Ticket.objects.exists())
        self.assertFalse(TicketAttachment.objects.exists())
        self.assertFalse([p for p in Path(self.directory.name).rglob('*') if p.is_file()])

    def test_expiry_and_cleanup_ignore_ticket_state_and_keep_metadata(self):
        for state, status in [('pending', 'open'), ('approved', 'closed'), ('rejected', 'closed')]:
            ticket, record = self.created()
            Ticket.objects.filter(pk=ticket.pk).update(state=state, status=status)
            TicketAttachment.objects.filter(pk=record.pk).update(date_created=timezone.now() - timedelta(days=31))
            self.assertEqual(self.download(ticket, record).status_code, 404)
            self.assertTrue(record.path.exists())
        fresh_ticket, fresh_record = self.created()
        cleanup_attachments()
        cleanup_attachments()
        self.assertEqual(TicketAttachment.objects.filter(purged_at__isnull=False).count(), 3)
        self.assertTrue(fresh_record.path.exists())
        self.assertEqual(Ticket.objects.filter(status='open').count(), 2)
        for record in TicketAttachment.objects.filter(purged_at__isnull=False):
            self.assertFalse(record.path.exists())
            self.assertTrue(TicketSerializer(record.ticket).data['attachments'][0]['expired'])

    def test_retention_changes_apply_to_existing_files_but_never_restore_purged_files(self):
        ticket, record = self.created()
        TicketAttachment.objects.filter(pk=record.pk).update(date_created=timezone.now() - timedelta(days=10))
        with override_settings(TICKET_ATTACHMENT_RETENTION_DAYS=7):
            self.assertEqual(self.download(ticket, record).status_code, 404)
            cleanup_attachments()
        with override_settings(TICKET_ATTACHMENT_RETENTION_DAYS=90):
            self.assertEqual(self.download(ticket, record).status_code, 404)
        for days, valid in [(0, False), (-1, False), (30, True)]:
            serializer = TicketSettingSerializer(data={'TICKET_ATTACHMENT_RETENTION_DAYS': days})
            self.assertEqual(serializer.is_valid(), valid, serializer.errors)

    def test_reapply_does_not_copy_or_rebind_attachments(self):
        ticket, record = self.created()
        request = APIRequestFactory().get('/')
        force_authenticate(request, self.applicant)
        response = TicketViewSet.as_view({'get': 'perform_action'}, **TicketViewSet.perform_action.kwargs)(
            request, pk=str(ticket.pk), action_name='reapply',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn('attachments', response.data)
        record.refresh_from_db()
        self.assertEqual(record.ticket_id, ticket.pk)
