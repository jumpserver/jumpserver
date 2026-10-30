import hashlib
import logging
import posixpath
import stat
from contextlib import contextmanager

import paramiko
from django.conf import settings

from libs.ansible.modules_utils.ssh_tunnel import TimeoutSSHTunnelForwarder


class TransferError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@contextmanager
def connection_address(asset, port):
    tunnel = None
    timeout = min(max(int(settings.SSH_GATEWAY_CONNECT_TIMEOUT), 1), 30)
    host = asset.address
    try:
        gateway = asset.gateway
        if asset.zone_id and asset.platform.gateway_enabled and not gateway:
            raise TransferError('gateway_unavailable')
        if gateway:
            credential = gateway.select_account
            if not credential:
                raise TransferError('gateway_unavailable')
            logger = logging.Logger(__name__, level=logging.CRITICAL + 1)
            logger.addHandler(logging.NullHandler())
            tunnel = TimeoutSSHTunnelForwarder(
                (gateway.address, gateway.port), ssh_username=credential.username,
                ssh_password=credential.password, ssh_pkey=credential.private_key_obj,
                connect_timeout=timeout, remote_bind_address=(host, port),
                local_bind_address=('127.0.0.1', 0), allow_agent=False, logger=logger,
            )
            tunnel.start()
            host, port = '127.0.0.1', tunnel.local_bind_port
        yield host, port
    finally:
        if tunnel:
            tunnel.stop()


@contextmanager
def connect(asset, account, port):
    client = paramiko.SSHClient()
    # Match the existing asset automation SSH host-key policy.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    timeout = min(max(int(settings.SSH_GATEWAY_CONNECT_TIMEOUT), 1), 30)
    try:
        with connection_address(asset, port) as (host, port):
            client.connect(host, port=port, username=account.username, password=account.password,
                           pkey=account.private_key_obj, timeout=timeout, banner_timeout=timeout,
                           auth_timeout=timeout, allow_agent=False, look_for_keys=False)
            with client.open_sftp() as sftp:
                sftp.get_channel().settimeout(30)
                yield sftp
    finally:
        client.close()


def transfer_root(sftp, asset, account, user):
    protocol = asset.platform.protocols.filter(name='sftp').first()
    root = protocol.setting.get('sftp_home', '') if protocol else '/tmp'
    home = sftp.normalize('.')
    if root.lower() in ('home', '~', ''):
        root = home
    else:
        for key, value in [('${HOME}', home), ('${ACCOUNT}', account.username), ('${USER}', user.username)]:
            root = root.replace(key, value)
        root = '/' + root.lstrip('/')
    return sftp.normalize(root)


def check_path(sftp, root, path, *, directory=False):
    # Reject links at every component, including parents of an upload destination.
    if posixpath.commonpath([root, path]) != root:
        raise TransferError('outside_root')
    current = '/'
    info = sftp.lstat(current)
    for part in path.strip('/').split('/'):
        if not part:
            continue
        current = posixpath.join(current, part)
        info = sftp.lstat(current)
        if stat.S_ISLNK(info.st_mode):
            raise TransferError('symlink_not_allowed')
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or sftp.normalize(path) != path:
        raise TransferError('invalid_file_type')
    return info


def upload(sftp, root, source, target, guard):
    from .storage import size_limit
    parent = posixpath.dirname(target)
    check_path(sftp, root, parent, directory=True)
    try:
        sftp.lstat(target)
    except FileNotFoundError:
        pass
    else:
        raise TransferError('destination_exists')
    digest = hashlib.sha256()
    with source.path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    if digest.hexdigest() != source.sha256 or source.path.stat().st_size != source.size:
        raise TransferError('source_changed')
    temp = posixpath.join(parent, f'.jms-transfer-{source.pk}')
    created, committing = False, False
    try:
        guard()
        with sftp.open(temp, 'wx') as output, source.path.open('rb') as stream:
            created = True
            sftp.chmod(temp, 0o600)
            digest, size = hashlib.sha256(), 0
            for chunk in iter(lambda: stream.read(65536), b''):
                guard()
                size += len(chunk)
                if size > size_limit():
                    raise TransferError('size_limit')
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != source.sha256 or size != source.size:
            raise TransferError('source_changed')
        guard(recheck=True)
        check_path(sftp, root, parent, directory=True)
        check_path(sftp, root, temp)
        # Standard SFTP rename refuses an existing destination; never use posix_rename.
        committing = True
        sftp.rename(temp, target)
        created = False
    except OSError as exc:
        if committing:
            raise TransferError('commit_uncertain') from exc
        raise
    finally:
        if created:
            try:
                check_path(sftp, root, parent, directory=True)
                sftp.remove(temp)
            except (OSError, TransferError):
                pass


def download(sftp, root, path, record, guard):
    from .storage import size_limit, write_file
    before = check_path(sftp, root, path)
    if before.st_size > size_limit():
        raise TransferError('size_limit')
    with sftp.open(path, 'rb') as stream:
        def chunks():
            while True:
                guard()
                chunk = stream.read(65536)
                if not chunk:
                    break
                yield chunk
        write_file(record, chunks())
        after = stream.stat()
    check_path(sftp, root, path)
    if (before.st_size, before.st_mtime) != (after.st_size, after.st_mtime) or record.size != before.st_size:
        record.path.unlink(missing_ok=True)
        raise TransferError('source_changed')
    guard(recheck=True)
