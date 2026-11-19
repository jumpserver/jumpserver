"""Bounded file transfers over the existing WinRM command/input streams."""
import base64
import gzip
import hashlib
import json
import ntpath
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from uuid import uuid4

from winrm.protocol import Protocol
from winrm.exceptions import WinRMError, WinRMOperationTimeoutError
from rest_framework.exceptions import ValidationError

from .policy import validate_path
from .transport import TransferError, connection_address

# Compress the fixed script to stay below the Windows command-line limit.
_payload = base64.b64encode(gzip.compress(Path(__file__).with_suffix('.ps1').read_bytes(), mtime=0)).decode('ascii')
_bootstrap = (
    "$m=[IO.MemoryStream]::new([Convert]::FromBase64String('" + _payload + "'));"
    "$z=[IO.Compression.GzipStream]::new($m,[IO.Compression.CompressionMode]::Decompress);"
    "$r=[IO.StreamReader]::new($z,[Text.Encoding]::UTF8);"
    "try { & ([ScriptBlock]::Create($r.ReadToEnd())) } finally { $r.Dispose(); $z.Dispose(); $m.Dispose() }"
)
SCRIPT = base64.b64encode(_bootstrap.encode('utf-16-le')).decode('ascii')
REMOTE_ERRORS = {'outside_root', 'symlink_not_allowed', 'invalid_file_type', 'destination_exists',
                 'source_changed', 'size_limit', 'file_missing', 'permission_denied', 'transfer_failed'}


def windows_path(path):
    try:
        return validate_path(path, windows=True)
    except ValidationError as exc:
        raise TransferError('invalid_path') from exc


class Connection:
    def __init__(self, protocol, shell):
        self.protocol, self.shell = protocol, shell

    def output(self, command):
        # The public pywinrm output helper retries operation timeouts indefinitely.
        deadline, output, size = time.monotonic() + 60, [], 0
        while time.monotonic() < deadline:
            try:
                stdout, _stderr, status, done = self.protocol._raw_get_command_output(self.shell, command)
            except WinRMOperationTimeoutError:
                continue
            size += len(stdout)
            if size > 1048576:
                raise OSError('WinRM file transfer response is too large')
            output.append(stdout)
            if done:
                return b''.join(output), status
        raise TimeoutError('WinRM file transfer command timed out')

    def invoke(self, parameters, chunks=()):
        command = self.protocol.run_command(self.shell, 'powershell.exe', [
            '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', SCRIPT,
        ], console_mode_stdin=False, skip_cmd_shell=True)
        ended = False
        try:
            header = base64.b64encode(json.dumps(parameters, ensure_ascii=True).encode()) + b'\r\n'
            try:
                self.protocol.send_command_input(self.shell, command, header)
                for chunk in chunks:
                    self.protocol.send_command_input(self.shell, command, chunk)
                self.protocol.send_command_input(self.shell, command, b'', end=True)
            except WinRMError:
                # A rejected destination can close stdin before the next chunk arrives.
                with suppress(Exception):
                    self.protocol.send_command_input(self.shell, command, b'', end=True)
            ended = True
            stdout, status = self.output(command)
            if status:
                raise OSError('WinRM file transfer command failed')
            result = json.loads(stdout.decode('utf-8-sig'))
            if result.get('error'):
                raise TransferError(result['error'] if result['error'] in REMOTE_ERRORS else 'transfer_failed')
            return result
        finally:
            if not ended:
                with suppress(Exception):
                    self.protocol.send_command_input(self.shell, command, b'', end=True)
                    self.output(command)
            with suppress(Exception):
                self.protocol.cleanup_command(self.shell, command)


@contextmanager
def connect(asset, account, port):
    options = asset.protocols.get(name='winrm', port=port).setting
    scheme = 'https' if options.get('use_ssl', port == 5986) else 'http'
    with connection_address(asset, port) as (host, remote_port):
        host = f'[{host}]' if ':' in host else host
        protocol = Protocol(endpoint=f'{scheme}://{host}:{remote_port}/wsman', transport='ntlm',
                            username=account.username, password=account.password,
                            server_cert_validation='ignore' if options.get('allow_invalid_cert', False) else 'validate',
                            operation_timeout_sec=20, read_timeout_sec=30)
        shell = None
        try:
            shell = protocol.open_shell(codepage=65001)
            yield Connection(protocol, shell)
        finally:
            if shell:
                with suppress(Exception):
                    protocol.close_shell(shell)
            with suppress(Exception):
                protocol.transport.close_session()


def transfer_root(connection, asset, account, user):
    options = asset.protocols.get(name='winrm').setting
    configured = options.get('file_transfer_root') or 'home'
    if configured.lower() != 'home':
        configured = windows_path(configured)
    result = connection.invoke({'action': 'root', 'root': configured})
    return windows_path(result['root'])


def upload(connection, root, source, target, guard):
    from .storage import size_limit
    target = windows_path(target)
    if source.size > size_limit():
        raise TransferError('size_limit')
    if source.path.stat().st_size != source.size:
        raise TransferError('source_changed')
    with source.path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != source.sha256:
            raise TransferError('source_changed')
    committing = False

    def chunks():
        nonlocal committing
        digest, size = hashlib.sha256(), 0
        with source.path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(65536), b''):
                guard()
                size += len(chunk)
                if size > size_limit():
                    raise TransferError('size_limit')
                digest.update(chunk)
                yield base64.b64encode(chunk) + b'\r\n'
        if size != source.size or digest.hexdigest() != source.sha256:
            raise TransferError('source_changed')
        guard(recheck=True)
        committing = True
        yield b'COMMIT\r\n'

    guard(recheck=True)
    try:
        result = connection.invoke({'action': 'upload', 'root': root, 'path': target,
                                    'temporary': ntpath.join(ntpath.dirname(target), f'.jms-transfer-{uuid4()}'),
                                    'size': source.size, 'sha256': source.sha256, 'limit': size_limit()}, chunks())
        if result.get('size') != source.size or result.get('sha256') != source.sha256:
            raise ValueError('Invalid transfer receipt')
    except TransferError:
        raise
    except Exception as exc:
        if committing:
            raise TransferError('commit_uncertain') from exc
        raise


def download(connection, root, path, record, guard):
    from .storage import size_limit, write_file
    path = windows_path(path)
    guard(recheck=True)
    parameters = {'root': root, 'path': path}
    before = connection.invoke({**parameters, 'action': 'stat'})
    if before['size'] > size_limit():
        raise TransferError('size_limit')

    def chunks():
        offset = 0
        while offset < before['size']:
            guard()
            count = min(524288, before['size'] - offset)
            result = connection.invoke({**parameters, 'action': 'read', 'offset': offset, 'count': count,
                                        'size': before['size'], 'mtime': before['mtime']})
            data = base64.b64decode(result['data'], validate=True)
            if len(data) != count:
                raise TransferError('source_changed')
            offset += len(data)
            yield data

    try:
        write_file(record, chunks())
        after = connection.invoke({**parameters, 'action': 'stat'})
        if before != after or record.size != before['size']:
            raise TransferError('source_changed')
        guard(recheck=True)
    except BaseException:
        record.path.unlink(missing_ok=True)
        raise
