import base64
import hashlib
import json
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from assets.models import Protocol
from tickets.models import TicketTransferExecution
from tickets.plugins.file_transfer import execution, winrm
from tickets.plugins.file_transfer.policy import validate_path
from tickets.plugins.file_transfer.transport import TransferError
from tickets.tests import test_file_transfer_execution as file_transfer


class WindowsPathTests(SimpleTestCase):
    def test_absolute_drive_paths_preserve_unicode_and_literal_characters(self):
        self.assertEqual(validate_path('c:/Users/test/中文 $file.txt', windows=True),
                         'c:\\Users\\test\\中文 $file.txt')
        self.assertEqual(validate_path('C:\\', windows=True), 'C:\\')

    def test_rejects_devices_streams_unc_relative_paths_and_ambiguous_names(self):
        for path in ['C:relative', '/tmp/file', '\\\\server\\share\\file', '\\\\?\\C:\\file',
                     'C:\\tmp\\..\\file', 'C:\\tmp\\.\\file', 'C:\\tmp\\a:stream',
                     'C:\\tmp\\nul.txt', 'C:\\tmp\\COM1', 'C:\\tmp\\lpt².txt', 'C:\\tmp\\CON .txt',
                     'C:\\tmp\\CONOUT$',
                     'C:\\tmp\\trailing.', 'C:\\tmp\\space ', 'C:\\tmp\\*', 'C:\\tmp\\a\x00']:
            with self.subTest(path=path), self.assertRaises(ValidationError):
                validate_path(path, windows=True)


class WinRMTransportTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def source(self, content):
        path = self.directory / 'source'
        path.write_bytes(content)
        return SimpleNamespace(path=path, size=len(content), sha256=hashlib.sha256(content).hexdigest())

    def protocol(self, result):
        protocol = Mock()
        protocol.run_command.return_value = 'command'
        protocol._raw_get_command_output.return_value = (json.dumps(result).encode(), b'', 0, True)
        return protocol

    def test_powershell_bootstrap_fits_windows_command_line_limit(self):
        self.assertLess(len(winrm.SCRIPT) + 150, 8191)

    def test_upload_streams_binary_chunks_and_checks_access_before_commit(self):
        for content in [b'', bytes(range(256)) * 600]:
            with self.subTest(size=len(content)):
                source = self.source(content)
                protocol = self.protocol({'size': source.size, 'sha256': source.sha256})
                guard = Mock()
                winrm.upload(winrm.Connection(protocol, 'shell'), 'C:\\tmp', source,
                             "C:\\tmp\\中文 '$file.bin", guard)
                inputs = [call.args[2] for call in protocol.send_command_input.call_args_list]
                header = json.loads(base64.b64decode(inputs[0]))
                self.assertEqual(header['path'], "C:\\tmp\\中文 '$file.bin")
                self.assertEqual(b''.join(base64.b64decode(chunk) for chunk in inputs[1:-2]), content)
                self.assertEqual(inputs[-2:], [b'COMMIT\r\n', b''])
                self.assertTrue(all(len(chunk) < 90000 for chunk in inputs))
                self.assertEqual(guard.call_args.kwargs, {'recheck': True})
                self.assertTrue(protocol.send_command_input.call_args.kwargs['end'])
                protocol.cleanup_command.assert_called_once_with('shell', 'command')

    def test_source_change_or_revocation_never_sends_commit(self):
        for revoked in (False, True):
            source = self.source(b'original')
            if not revoked:
                source.path.write_bytes(b'changed')
            protocol = self.protocol({})
            guard = Mock(side_effect=[None, None, PermissionDenied('revoked')]) if revoked else Mock()
            error = PermissionDenied if revoked else TransferError
            with self.subTest(revoked=revoked), self.assertRaises(error):
                winrm.upload(winrm.Connection(protocol, 'shell'), 'C:\\tmp', source, 'C:\\tmp\\file', guard)
            self.assertNotIn(b'COMMIT\r\n', [c.args[2] for c in protocol.send_command_input.call_args_list])
            if revoked:
                self.assertTrue(protocol.send_command_input.call_args.kwargs['end'])
                protocol.cleanup_command.assert_called_once()
            else:
                protocol.run_command.assert_not_called()

    def test_lost_receipt_is_uncertain_and_reported_remote_errors_are_preserved(self):
        source = self.source(b'payload')
        for failure, expected in [(OSError('lost reply'), 'commit_uncertain'),
                                  (None, 'destination_exists')]:
            protocol = self.protocol({'error': 'destination_exists'})
            if failure:
                protocol._raw_get_command_output.side_effect = failure
            with self.subTest(error=expected), self.assertRaisesMessage(TransferError, expected):
                winrm.upload(winrm.Connection(protocol, 'shell'), 'C:\\tmp', source, 'C:\\tmp\\file', Mock())

    def test_command_timeout_and_excessive_output_are_bounded_and_cleaned_up(self):
        protocol = self.protocol({})
        protocol._raw_get_command_output.side_effect = winrm.WinRMOperationTimeoutError()
        with patch.object(winrm.time, 'monotonic', side_effect=[0, 0, 61]):
            with self.assertRaises(TimeoutError):
                winrm.Connection(protocol, 'shell').invoke({'action': 'stat', 'path': 'C:\\tmp\\file'})
        protocol.cleanup_command.assert_called_once()
        protocol = self.protocol({})
        protocol._raw_get_command_output.return_value = (b'x' * 1048577, b'', 0, True)
        with self.assertRaises(OSError):
            winrm.Connection(protocol, 'shell').invoke({'action': 'stat', 'path': 'C:\\tmp\\file'})
        protocol.cleanup_command.assert_called_once()

    def test_early_remote_rejection_recovers_error_from_closed_stdin(self):
        source = self.source(b'payload')
        protocol = self.protocol({'error': 'destination_exists'})
        protocol.send_command_input.side_effect = [None, winrm.WinRMError('pipe closed'), None]
        with self.assertRaisesMessage(TransferError, 'destination_exists'):
            winrm.upload(winrm.Connection(protocol, 'shell'), 'C:\\tmp', source, 'C:\\tmp\\file', Mock())
        protocol.cleanup_command.assert_called_once()

    def test_root_uses_account_home_by_default_and_rejects_invalid_configuration(self):
        asset = SimpleNamespace(protocols=Mock())
        asset.protocols.get.return_value.setting = {}
        connection = Mock()
        connection.invoke.return_value = {'root': 'C:\\Users\\reviewer'}
        self.assertEqual(winrm.transfer_root(connection, asset, None, None), 'C:\\Users\\reviewer')
        connection.invoke.assert_called_once_with({'action': 'root', 'root': 'home'})
        asset.protocols.get.return_value.setting = {'file_transfer_root': '\\\\server\\share'}
        with self.assertRaisesMessage(TransferError, 'invalid_path'):
            winrm.transfer_root(connection, asset, None, None)

    def test_download_is_chunked_and_removes_partial_files_when_source_changes(self):
        content = bytes(range(256)) * 3000
        for changed in (False, True):
            record = SimpleNamespace(path=self.directory / 'download', save=Mock())
            calls = []

            def invoke(parameters):
                calls.append(parameters)
                if parameters['action'] == 'stat':
                    return {'size': len(content), 'mtime': '2' if changed and len(calls) > 1 else '1'}
                self.assertEqual(parameters['mtime'], '1')
                chunk = content[parameters['offset']:parameters['offset'] + parameters['count']]
                return {'data': base64.b64encode(chunk).decode()}

            connection = SimpleNamespace(invoke=invoke)
            with self.subTest(changed=changed):
                if changed:
                    with self.assertRaisesMessage(TransferError, 'source_changed'):
                        winrm.download(connection, 'C:\\tmp', 'C:\\tmp\\file', record, Mock())
                    self.assertFalse(record.path.exists())
                else:
                    winrm.download(connection, 'C:\\tmp', 'C:\\tmp\\file', record, Mock())
                    self.assertEqual(record.path.read_bytes(), content)
                    self.assertEqual(record.sha256, hashlib.sha256(content).hexdigest())
                    record.path.unlink()
                self.assertEqual([p['offset'] for p in calls if p['action'] == 'read'], [0, 524288])

    @override_settings(FILE_UPLOAD_SIZE_LIMIT_MB=1)
    def test_oversized_download_never_reads_or_creates_a_file(self):
        connection = Mock()
        connection.invoke.return_value = {'size': 1048577, 'mtime': '1'}
        record = SimpleNamespace(path=self.directory / 'download')
        with self.assertRaisesMessage(TransferError, 'size_limit'):
            winrm.download(connection, 'C:\\tmp', 'C:\\tmp\\file', record, Mock())
        self.assertFalse(record.path.exists())
        self.assertEqual(connection.invoke.call_count, 1)

    def test_connection_uses_platform_tls_policy_and_closes_shell_and_http_session(self):
        account = SimpleNamespace(username='DOMAIN\\user', password='secret')
        for invalid in (False, True):
            options = {'use_ssl': True, 'allow_invalid_cert': invalid}
            asset = SimpleNamespace(protocols=Mock())
            asset.protocols.get.return_value.setting = options

            @contextmanager
            def address(*args):
                yield 'windows.example', 5986

            with patch.object(winrm, 'connection_address', address), patch.object(winrm, 'Protocol') as factory:
                with winrm.connect(asset, account, 5986):
                    pass
                self.assertEqual(factory.call_args.kwargs['endpoint'], 'https://windows.example:5986/wsman')
                self.assertEqual(factory.call_args.kwargs['server_cert_validation'], 'ignore' if invalid else 'validate')
                factory.return_value.close_shell.assert_called_once()
                factory.return_value.transport.close_session.assert_called_once()


class WindowsFileTransferTests(TestCase):
    setUpTestData = file_transfer.FileTransferExecutionTests.__dict__['setUpTestData']
    workflow = file_transfer.FileTransferExecutionTests.workflow
    task = file_transfer.FileTransferExecutionTests.task
    payload = file_transfer.FileTransferExecutionTests.payload
    serializer = file_transfer.FileTransferExecutionTests.serializer
    grant = file_transfer.FileTransferExecutionTests.grant
    upload = file_transfer.FileTransferExecutionTests.upload
    request_ticket = file_transfer.FileTransferExecutionTests.request_ticket
    action = file_transfer.FileTransferExecutionTests.action

    def setUp(self):
        file_transfer.FileTransferExecutionTests.setUp(self)
        self.asset.platform.type = 'windows'
        self.asset.platform.save(update_fields=['type'])
        Protocol.objects.create(asset=self.asset, name='winrm', port=5985)
        self.base.protocols = ['winrm']
        self.base.save(update_fields=['protocols'])

    def test_windows_upload_freezes_paths_and_worker_uses_winrm(self):
        ticket, instance = self.request_ticket(target_directory='C:\\Users\\root\\Downloads')
        self.assertEqual(instance.context['transfer_protocol'], 'winrm')
        result = self.plugin.get_result(ticket, self.applicant)
        self.assertEqual(result['files'][0]['path'], 'C:\\Users\\root\\Downloads\\hello.txt')
        self.assertEqual(self.action(ticket).status_code, 202)
        with patch.object(winrm, 'connect'), patch.object(winrm, 'transfer_root', return_value='C:\\Users\\root'), \
                patch.object(winrm, 'upload') as upload:
            execution.execute(ticket.pk)
        self.assertEqual(upload.call_args.args[3], result['files'][0]['path'])
        self.assertEqual(TicketTransferExecution.objects.get(ticket=ticket).state, 'success')

    def test_windows_download_has_correct_filename_and_rechecks_protocol_and_platform(self):
        ticket, _ = self.request_ticket(direction='download', paths=['C:\\Users\\root\\中文.txt'])
        self.assertEqual(self.plugin.get_result(ticket, self.applicant)['files'][0]['name'], '中文.txt')
        self.base.protocols = ['rdp']
        self.base.save(update_fields=['protocols'])
        self.assertEqual(self.action(ticket).status_code, 403)
        self.base.protocols = ['winrm']
        self.base.save(update_fields=['protocols'])
        self.asset.platform.type = 'linux'
        self.asset.platform.save(update_fields=['type'])
        self.assertEqual(self.action(ticket).status_code, 403)

    def test_windows_requires_winrm_password_access_and_rejects_duplicate_paths(self):
        data = self.payload('file_transfer', asset=str(self.asset.pk), accounts=['root'], direction='download',
                            paths=['C:\\tmp\\file', 'c:\\TMP\\FILE'])
        self.assertFalse(self.serializer(data).is_valid())
        data['request_data']['paths'] = ['C:\\tmp\\file']
        self.base.protocols = ['ssh', 'rdp']
        self.base.save(update_fields=['protocols'])
        self.assertFalse(self.serializer(data).is_valid())
        self.base.protocols = ['winrm']
        self.base.save(update_fields=['protocols'])
        self.account.secret_type = 'ssh_key'
        self.account.save(update_fields=['secret_type'])
        self.assertFalse(self.serializer(data).is_valid())

    def test_windows_upload_rejects_case_collisions_and_device_filenames(self):
        for names in [('File.txt', 'file.TXT'), ('NUL.txt',)]:
            files = [str(self.upload(name=name).pk) for name in names]
            data = self.payload('file_transfer', asset=str(self.asset.pk), accounts=['root'], direction='upload',
                                target_directory='C:\\tmp', files=files)
            with self.subTest(names=names):
                self.assertFalse(self.serializer(data).is_valid())
