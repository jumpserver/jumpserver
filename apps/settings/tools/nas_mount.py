# -*- coding: utf-8 -*-
#
import os
import subprocess
import tempfile

from common.utils import get_logger

logger = get_logger(__file__)


def is_nas_mounted(mount_path):
    """Check if the given path is a mount point."""
    if not mount_path or not os.path.exists(mount_path):
        return False
    return os.path.ismount(mount_path)


def _probe_nas_writable(mount_path):
    """Best-effort write probe to confirm the NAS is actually reachable.

    Existing mount points can stays mounted even when the NAS goes offline
    (NFS/CIFS keep retrying in the background). A plain ``ismount`` therefore
    does not prove the NAS is usable. Creating-and-removing a temp file forces
    the filesystem to contact the server; with ``soft`` mount options a late
    reply aborts in bounded time and the probe returns False.

    Returns True if the NAS is writable/reachable, False otherwise.
    """
    if not mount_path or not os.path.isdir(mount_path):
        return False
    try:
        fd, tmp = tempfile.mkstemp(dir=mount_path, prefix='.jumpserver_nas_probe_')
        os.write(fd, b'probe')
        os.close(fd)
        os.remove(tmp)
        return True
    except OSError as e:
        logger.error('NAS writability probe failed on %s: %s', mount_path, e)
        return False


def ensure_nas_mounted(config, force=False):
    """Ensure NAS is mounted. Returns True if mounted/already mounted, False on failure.

    Args:
        config: dict with nas_enabled, nas_type, nas_host, etc.
        force: If True, unmount and re-mount even if already mounted.
               Use True when user changes NAS config, False on startup."""
    logger.info('Checking NAS mount status...')
    nas_enabled = config.get('nas_enabled', False)
    if not nas_enabled:
        if force:
            _unmount_if_needed(config)
        return False

    host = config.get('nas_host', '')
    share_name = config.get('nas_share_name', '')
    mount_path = config.get('nas_mount_path', '')
    nas_type = config.get('nas_type', 'nfs')

    if not host or not share_name or not mount_path:
        logger.info('NAS config incomplete, skip mount')
        return False

    if is_nas_mounted(mount_path):
        if not force:
            if _probe_nas_writable(mount_path):
                logger.info('NAS already mounted and writable at %s', mount_path)
                return True
            logger.warning('NAS mount point exists but is not writable, re-mounting %s', mount_path)
        _unmount(mount_path)

    if not os.path.exists(mount_path):
        try:
            os.makedirs(mount_path, exist_ok=True)
            logger.info('Created NAS mount path: %s', mount_path)
        except OSError as e:
            logger.error('Failed to create mount path %s: %s', mount_path, e)
            return False

    # Build mount command
    nas_port = config.get('nas_port', 0) or 0
    if nas_type == 'cifs':
        source = f'//{host}/{share_name}'
        password = config.get('nas_password', '') or ''
        password = password.replace(',', '\\,')
        username = config.get('nas_username', '') or ''
        options = [
            f'username={username}',
            f'password={password}',
            'soft',
        ]
        if nas_port:
            options.append(f'port={nas_port}')
        cmd = ['mount', '-t', 'cifs', '-o', ','.join(options), source, mount_path]
    else:
        source = f'{host}:{share_name}'
        # NFS "soft" mount: return an I/O error after timeo*retrans instead of
        # blocking forever on an unreachable server. timeo=600 = 10s per retry,
        # retrans=2 responses, so the whole op fails in ~a few tens of seconds.
        options = [
            'soft',
            'timeo=600',
            'retrans=2',
        ]
        if nas_port:
            options.append(f'port={nas_port}')
        cmd = ['mount', '-t', 'nfs', '-o', ','.join(options), source, mount_path]

    logger.info('Mounting NAS: %s -> %s (type=%s)', source, mount_path, nas_type)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info('NAS mounted successfully: %s -> %s', source, mount_path)
            return True
        else:
            logger.error('NAS mount failed: %s', result.stderr.strip())
            return False
    except subprocess.TimeoutExpired:
        logger.error('NAS mount timed out: %s -> %s', source, mount_path)
        return False
    except FileNotFoundError:
        logger.error('mount command not found, is this Linux?')
        return False


def _unmount(mount_path):
    """Unmount the given path."""
    logger.info('Unmounting %s', mount_path)
    try:
        result = subprocess.run(['umount', mount_path], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info('Unmounted successfully: %s', mount_path)
        else:
            logger.warning('Unmount failed (may already be unmounted): %s', result.stderr.strip())
    except subprocess.TimeoutExpired:
        logger.warning('Unmount timed out: %s', mount_path)
    except FileNotFoundError:
        logger.warning('umount command not found')


def _unmount_if_needed(config):
    """Unmount NAS if currently mounted (e.g. when NAS is disabled)."""
    mount_path = config.get('nas_mount_path', '')
    if mount_path and is_nas_mounted(mount_path):
        _unmount(mount_path)
