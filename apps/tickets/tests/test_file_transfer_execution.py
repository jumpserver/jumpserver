import stat
import tempfile
from pathlib import Path
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.signals import request_finished
from django.db import transaction
from django.db import close_old_connections
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Account
from assets.models import Protocol
from orgs.utils import tmp_to_root_org
from perms.models import AssetPermission
from tickets.api.plugin import TicketTypeViewSet
from tickets.api.ticket import TicketViewSet
from tickets.models import TicketTransferFile, TicketTransferExecution
from tickets.plugins import get_ticket_plugin
from tickets.plugins.file_transfer import execution, transport
from tickets.plugins.file_transfer.policy import validate_path
from tickets.plugins.file_transfer.storage import stage_upload
from tickets.tests import test_file_transfer as legacy
from tickets.tests import test_plugins as helpers
from tickets.workflow.business import submit_ticket


class FileTransferExecutionTests(TestCase):
    setUpTestData = helpers.TicketPluginTests.__dict__['setUpTestData']
    workflow = helpers.TicketPluginTests.workflow
    task = helpers.TicketPluginTests.task
    payload = helpers.TicketPluginTests.payload
    serializer = helpers.TicketPluginTests.serializer
    grant = legacy.FileTransferTests.grant

    def setUp(self):
        helpers.TicketPluginTests.setUp(self)
        patcher = patch('accounts.signal_handlers.push_accounts_if_need.delay')
        patcher.start()
        self.addCleanup(patcher.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.override = override_settings(SHARE_DIR=directory.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        request_finished.disconnect(close_old_connections)
        self.addCleanup(request_finished.connect, close_old_connections)
        self.account = Account.objects.create(asset=self.asset, name='root', username='root', secret='never-log-secret')
        Protocol.objects.create(asset=self.asset, name='ssh', port=22)
        self.base = self.grant()
        self.plugin = get_ticket_plugin('file_transfer')

    def upload(self, name='hello.txt', data=b'approved content'):
        return stage_upload(self.applicant, str(self.org.pk), SimpleUploadedFile(name, data))

    def request_ticket(self, approved=True, direction='upload', **changes):
        parameters = {'asset': str(self.asset.pk), 'accounts': ['root'], 'direction': direction, 'duration': 600}
        if direction == 'upload':
            parameters.update(target_directory='/tmp', files=[str(self.upload().pk)])
        else:
            parameters['paths'] = ['/tmp/hello.txt']
        parameters.update(changes)
        serializer = self.serializer(self.payload('file_transfer', **parameters))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket = serializer.save()
        instance = submit_ticket(ticket)
        if approved:
            self.engine.approve(self.task(instance), self.alice)
            ticket.refresh_from_db()
            instance.refresh_from_db()
            self.assertEqual(instance.state, 'approved', list(instance.events.values('type', 'data')))
        return ticket, instance

    def action(self, ticket, name='execute_transfer', user=None, data=None, method='post'):
        request = getattr(APIRequestFactory(), method)('/', data or {}, format='json')
        force_authenticate(request, user or self.applicant)
        with transaction.atomic():
            return TicketViewSet.as_view({method: 'perform_action'}, **TicketViewSet.perform_action.kwargs)(
                request, pk=ticket.pk, action_name=name)

    def test_approval_is_manual_and_does_not_grant_global_actions(self):
        ticket, instance = self.request_ticket()
        self.assertFalse(AssetPermission.objects.filter(pk=ticket.pk).exists())
        self.assertFalse(TicketTransferExecution.objects.exists())
        self.assertEqual(self.plugin.get_result(ticket, self.applicant)['state'], 'ready')
        with patch('tickets.plugins.file_transfer.actions.dispatch') as dispatch, self.captureOnCommitCallbacks(execute=True):
            response = self.action(ticket)
            self.assertEqual(response.status_code, 202, response.data)
            self.assertEqual(self.action(ticket).status_code, 202)
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(TicketTransferExecution.objects.count(), 1)
        job = TicketTransferExecution.objects.get(ticket=ticket)
        self.assertEqual(job.files[0]['path'], '/tmp/hello.txt')
        self.assertNotIn('never-log-secret', str(instance.context) + str(job.files))

    def test_pending_other_user_expired_and_changed_permissions_cannot_execute(self):
        ticket, instance = self.request_ticket(approved=False)
        self.assertEqual(self.action(ticket).status_code, 403)
        self.engine.approve(self.task(instance), self.alice)
        ticket.refresh_from_db()
        self.assertEqual(self.action(ticket, user=self.alice).status_code, 403)
        self.assertEqual(self.action(ticket, data={'path': '/etc/passwd'}).status_code, 400)
        self.base.is_active = False
        self.base.save(update_fields=['is_active'])
        self.assertEqual(self.action(ticket).status_code, 403)
        self.base.is_active = True
        self.base.save(update_fields=['is_active'])
        instance.date_finished = timezone.now() - timedelta(hours=1)
        instance.save(update_fields=['date_finished'])
        self.assertEqual(self.action(ticket).status_code, 403)
        self.assertFalse(TicketTransferExecution.objects.exists())

    def test_file_identity_ownership_and_single_claim(self):
        record = self.upload()
        ticket, _ = self.request_ticket(files=[str(record.pk)])
        data = self.payload('file_transfer', asset=str(self.asset.pk), accounts=['root'], direction='upload',
                            target_directory='/tmp', files=[str(record.pk)])
        self.assertFalse(self.serializer(data).is_valid())
        response = self.action(ticket, 'review_transfer_file', user=self.alice,
                               data={'file_id': str(record.pk)}, method='get')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'approved content')
        response.close()
        self.assertIn(self.action(ticket, 'review_transfer_file', user=self.bob,
                                  data={'file_id': str(record.pk)}, method='get').status_code, [403, 404])

    def test_paths_and_unsupported_targets_are_rejected(self):
        for path in ('relative/file', '/tmp/../etc/passwd', '/tmp/*', '/tmp/a\x00', '//tmp/file'):
            with self.subTest(path=path):
                data = self.payload('file_transfer', asset=str(self.asset.pk), accounts=['root'],
                                    direction='download', paths=[path])
                self.assertFalse(self.serializer(data).is_valid())
        self.asset.platform.type = 'windows'
        self.asset.platform.save(update_fields=['type'])
        data = self.payload('file_transfer', asset=str(self.asset.pk), accounts=['root'],
                            direction='download', paths=['/tmp/file'])
        self.assertFalse(self.serializer(data).is_valid())

    def test_worker_is_single_use_and_rechecks_revoked_access(self):
        ticket, _ = self.request_ticket()
        self.action(ticket)
        self.base.delete()
        with patch.object(transport, 'connect') as connect:
            execution.execute(ticket.pk)
            execution.execute(ticket.pk)
        connect.assert_not_called()
        job = TicketTransferExecution.objects.get(ticket=ticket)
        self.assertEqual(job.state, 'failed')
        self.assertEqual(job.files[0]['error'], 'access_changed')

    def test_connection_acl_and_explicit_exclusions_block_execution(self):
        from perms.const import ActionChoices
        ticket, _ = self.request_ticket()
        with patch('ops.models.job.match_rejected_login_asset_acl', return_value=(self.asset, object())):
            self.assertEqual(self.action(ticket).status_code, 403)
        self.grant(accounts=['!root'], actions=ActionChoices.upload)
        self.assertEqual(self.action(ticket).status_code, 403)
        self.assertFalse(TicketTransferExecution.objects.exists())

    def test_download_uses_approved_paths_and_preserves_partial_results(self):
        ticket, _ = self.request_ticket(direction='download', paths=['/tmp/hello.txt', '/tmp/missing.txt'])
        ticket.request_data['paths'] = ['/etc/unapproved']
        ticket.save(update_fields=['request_data'])
        self.action(ticket)
        def download(sftp, root, path, record, guard):
            from tickets.plugins.file_transfer.storage import write_file
            if path == '/tmp/missing.txt':
                raise FileNotFoundError()
            self.assertEqual(path, '/tmp/hello.txt')
            return write_file(record, [b'approved result'])
        with patch.object(transport, 'connect'), patch.object(transport, 'transfer_root', return_value='/tmp'), \
                patch.object(transport, 'download', side_effect=download) as transfer:
            execution.execute(ticket.pk)
            execution.execute(ticket.pk)
        self.assertEqual(transfer.call_count, 2)
        job = TicketTransferExecution.objects.get(ticket=ticket)
        self.assertEqual(job.state, 'failed')
        self.assertEqual([item['state'] for item in job.files], ['success', 'failed'])
        result = self.plugin.get_result(ticket, self.applicant)
        self.assertEqual([action['file_id'] for action in result['actions']], [job.files[0]['id']])

    def test_interrupted_execution_is_not_replayed_and_active_files_are_not_purged(self):
        ticket, _ = self.request_ticket()
        self.action(ticket)
        record = ticket.transfer_files.get()
        TicketTransferFile.objects.filter(pk=record.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        TicketTransferExecution.objects.filter(ticket=ticket).update(state='running', date_started=timezone.now())
        execution.maintain()
        self.assertEqual(execution.cleanup(), 0)
        self.assertTrue(record.path.exists())
        TicketTransferExecution.objects.filter(ticket=ticket).update(date_started=timezone.now() - timedelta(minutes=20))
        with patch.object(transport, 'connect') as connect:
            execution.maintain()
            execution.execute(ticket.pk)
        connect.assert_not_called()
        job = TicketTransferExecution.objects.get(ticket=ticket)
        self.assertEqual(job.state, 'unverified')
        self.assertEqual(job.files[0]['error'], 'interrupted')
        self.assertTrue(record.path.exists())
        self.assertEqual(execution.cleanup(), 1)
        self.assertFalse(record.path.exists())

    def test_recovery_redispatches_only_due_queued_transfers_without_cleaning_files(self):
        ticket, _ = self.request_ticket()
        self.action(ticket)
        record = ticket.transfer_files.get()
        TicketTransferFile.objects.filter(pk=record.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with patch('tickets.tasks.execute_ticket_file_transfer.delay') as delay:
            self.assertEqual(execution.maintain(), 1)
            self.assertEqual(execution.maintain(), 0)
            delay.assert_called_once_with(str(ticket.pk))
            TicketTransferExecution.objects.filter(ticket=ticket).update(
                dispatch_after=timezone.now() - timedelta(seconds=1))
            self.assertEqual(execution.maintain(), 1)
            self.assertEqual(delay.call_count, 2)
        self.assertTrue(record.path.exists())

    def test_cleanup_drains_multiple_batches_across_organizations(self):
        retained = self.upload()
        with tmp_to_root_org():
            files = TicketTransferFile.objects.bulk_create([
                TicketTransferFile(id=UUID(int=i + 1), owner=self.applicant if i < 100 else self.alice,
                                   org_id=self.org.pk if i % 2 else self.other_org.pk,
                                   name=f'{i}.txt', kind='upload' if i % 2 else 'download',
                                   expires_at=timezone.now() - timedelta(hours=1))
                for i in range(205)
            ])
            self.assertEqual(TicketTransferFile.objects.values('org_id').distinct().count(), 2)
        for record in files:
            record.path.parent.mkdir(parents=True, exist_ok=True)
            record.path.write_bytes(b'expired content')
        self.assertEqual(execution.cleanup(), 205)
        self.assertTrue(all(not record.path.exists() for record in files))
        with tmp_to_root_org():
            self.assertEqual(TicketTransferFile.objects.filter(purged_at__isnull=False).count(), 205)
        self.assertTrue(retained.path.exists())
        self.assertEqual(execution.cleanup(), 0)

    def test_cleanup_retries_failed_deletions_and_tolerates_missing_files(self):
        failed, missing, other = sorted([self.upload() for _ in range(3)], key=lambda record: record.pk)
        TicketTransferFile.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        missing.path.unlink()
        unlink = Path.unlink

        def delete(path, **kwargs):
            if path == failed.path:
                raise PermissionError('Cannot remove file')
            return unlink(path, **kwargs)

        with patch.object(Path, 'unlink', delete), self.assertLogs(execution.logger, level='ERROR'):
            self.assertEqual(execution.cleanup(), 2)
        failed.refresh_from_db()
        self.assertIsNone(failed.purged_at)
        self.assertTrue(failed.path.exists())
        self.assertFalse(other.path.exists())
        self.assertEqual(execution.cleanup(), 1)
        self.assertFalse(failed.path.exists())
        self.assertEqual(execution.cleanup(), 0)

    def test_cleanup_removes_terminated_ticket_files_and_preserves_pending_files(self):
        pending_ticket, _ = self.request_ticket(approved=False)
        retained = pending_ticket.transfer_files.get()
        for state in ('rejected', 'closed', 'cancelled', 'expired', 'error'):
            with self.subTest(state=state):
                ticket, _ = self.request_ticket(approved=False)
                record = ticket.transfer_files.get()
                ticket.state = state
                ticket.save(update_fields=['state'])
                self.assertEqual(execution.cleanup(), 1)
                self.assertFalse(record.path.exists())
                self.assertTrue(retained.path.exists())

    def test_cleanup_rechecks_expiry_and_running_state_after_batch_selection(self):
        select_for_update = TicketTransferFile.objects.select_for_update
        for change in ('extend_expiry', 'start_transfer'):
            with self.subTest(change=change):
                ticket, _ = self.request_ticket()
                self.action(ticket)
                record = ticket.transfer_files.get()
                TicketTransferFile.objects.filter(pk=record.pk).update(
                    expires_at=timezone.now() - timedelta(seconds=1))

                def update_before_lock():
                    if change == 'extend_expiry':
                        TicketTransferFile.objects.filter(pk=record.pk).update(
                            expires_at=timezone.now() + timedelta(hours=1))
                    else:
                        TicketTransferExecution.objects.filter(ticket=ticket).update(
                            state='running', date_started=timezone.now())
                    return select_for_update()

                with patch.object(TicketTransferFile.objects, 'select_for_update', side_effect=update_before_lock):
                    self.assertEqual(execution.cleanup(), 0)
                record.refresh_from_db()
                self.assertIsNone(record.purged_at)
                self.assertTrue(record.path.exists())

    def test_periodic_registration_upgrades_recovery_and_adds_hourly_cleanup(self):
        from django_celery_beat.models import PeriodicTask
        from ops.celery.decorator import get_register_period_tasks
        from ops.celery.utils import create_or_update_celery_periodic_tasks
        from tickets.tasks import maintain_ticket_file_transfers, cleanup_ticket_transfer_files

        recovery = maintain_ticket_file_transfers.name
        cleanup = cleanup_ticket_transfer_files.name
        create_or_update_celery_periodic_tasks({recovery: {'task': recovery, 'interval': 60}})
        for definition in get_register_period_tasks():
            if recovery in definition or cleanup in definition:
                create_or_update_celery_periodic_tasks(definition)
        self.assertEqual(PeriodicTask.objects.get(name=recovery).interval.every, 300)
        self.assertEqual(PeriodicTask.objects.get(name=cleanup).interval.every, 3600)
        self.assertEqual(PeriodicTask.objects.filter(name__in=[recovery, cleanup]).count(), 2)

    def test_download_only_exposes_successful_file_to_applicant_until_expiry(self):
        ticket, _ = self.request_ticket(direction='download')
        self.action(ticket)
        with patch.object(transport, 'connect') as connect, patch.object(transport, 'transfer_root', return_value='/tmp'):
            connect.return_value.__enter__.return_value = SimpleNamespace()
            def download(sftp, root, path, record, guard):
                from tickets.plugins.file_transfer.storage import write_file
                guard(recheck=True)
                write_file(record, [b'remote file'])
            with patch.object(transport, 'download', side_effect=download):
                execution.execute(ticket.pk)
        job = TicketTransferExecution.objects.get(ticket=ticket)
        self.assertEqual(job.state, 'success', job.files)
        record = TicketTransferFile.objects.get(pk=job.files[0]['id'])
        response = self.action(ticket, 'download_transfer_file', data={'file_id': str(record.pk)}, method='get')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'remote file')
        response.close()
        self.assertEqual(self.action(ticket, 'download_transfer_file', user=self.alice,
                                     data={'file_id': str(record.pk)}, method='get').status_code, 403)
        TicketTransferFile.objects.filter(pk=record.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(record.path.exists())
        self.assertEqual(self.action(ticket, 'download_transfer_file',
                                     data={'file_id': str(record.pk)}, method='get').status_code, 404)
        execution.cleanup()
        self.assertFalse(record.path.exists())

    def test_upload_api_limits_membership_and_file_size(self):
        request = APIRequestFactory().post('/', {'org_id': self.other_org.pk,
                                                 'file': SimpleUploadedFile('a', b'a')})
        force_authenticate(request, self.applicant)
        response = TicketTypeViewSet.as_view({'post': 'upload_file'})(request, pk='file_transfer')
        self.assertEqual(response.status_code, 403)
        with override_settings(FILE_UPLOAD_SIZE_LIMIT_MB=1):
            with self.assertRaises(Exception):
                self.upload(data=b'x' * (1024 * 1024 + 1))

    def test_real_ssh_sftp_roundtrip_no_overwrite_and_symlink_rejection(self):
        from tickets.tests.sftp_server import serve
        from tickets.plugins.file_transfer.policy import expires_at
        ticket, _ = self.request_ticket()
        record = ticket.transfer_files.get()
        with tempfile.TemporaryDirectory() as remote:
            target = Path(remote) / 'tmp'
            target.mkdir()
            with serve(remote) as sftp:
                transport.upload(sftp, '/tmp', record, '/tmp/hello.txt', lambda **kw: None)
                self.assertEqual((target / 'hello.txt').read_bytes(), b'approved content')
                with self.assertRaisesMessage(transport.TransferError, 'destination_exists'):
                    transport.upload(sftp, '/tmp', record, '/tmp/hello.txt', lambda **kw: None)
                (target / 'link').symlink_to(target / 'hello.txt')
                with self.assertRaisesMessage(transport.TransferError, 'symlink_not_allowed'):
                    transport.check_path(sftp, '/tmp', '/tmp/link')
                download = TicketTransferFile.objects.create(
                    owner=self.applicant, ticket=ticket, name='hello.txt', kind='download',
                    expires_at=expires_at(ticket),
                )
                transport.download(sftp, '/tmp', '/tmp/hello.txt', download, lambda **kw: None)
                self.assertEqual(download.path.read_bytes(), b'approved content')
                self.assertEqual(download.sha256, record.sha256)
                record.path.write_bytes(b'tampered content')
                with self.assertRaisesMessage(transport.TransferError, 'source_changed'):
                    transport.upload(sftp, '/tmp', record, '/tmp/other.txt', lambda **kw: None)
                self.assertFalse((target / 'other.txt').exists())


class TransferPathTests(SimpleTestCase):
    def test_regular_paths_are_literal_and_links_or_outside_root_are_rejected(self):
        self.assertEqual(validate_path('/tmp/a b,$file'), '/tmp/a b,$file')
        sftp = SimpleNamespace(
            lstat=lambda p: SimpleNamespace(st_mode=stat.S_IFLNK if p == '/tmp/link' else stat.S_IFREG),
            normalize=lambda p: p,
        )
        with self.assertRaisesMessage(transport.TransferError, 'symlink_not_allowed'):
            transport.check_path(sftp, '/tmp', '/tmp/link/file')
        with self.assertRaisesMessage(transport.TransferError, 'outside_root'):
            transport.check_path(sftp, '/tmp', '/tmp-other/file')
