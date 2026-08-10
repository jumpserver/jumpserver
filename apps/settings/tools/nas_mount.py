# -*- coding: utf-8 -*-
#
import os
import subprocess

from common.utils import get_logger

logger = get_logger(__file__)


def is_nas_mounted(mount_path):
    """Check if the given path is a mount point."""
    if not mount_path or not os.path.exists(mount_path):
        return False
    return os.path.ismount(mount_path)


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
            logger.info('NAS already mounted at %s', mount_path)
            return True
        _unmount(mount_path)

    if not os.path.exists(mount_path):
        try:
            os.makedirs(mount_path, exist_ok=True)
            logger.info('Created NAS mount path: %s', mount_path)
        except OSError as e:
            logger.error('Failed to create mount path %s: %s', mount_path, e)
            return False

    # Build mount command
    if nas_type == 'cifs':
        source = f'//{host}/{share_name}'
        password = config.get('nas_password', '') or ''
        password = password.replace(',', '\\,')
        username = config.get('nas_username', '') or ''
        cmd = ['mount', '-t', 'cifs', '-o', f'username={username},password={password}',
               source, mount_path]
    else:
        source = f'{host}:{share_name}'
        cmd = ['mount', '-t', 'nfs', source, mount_path]

    logger.info('Mounting NAS: %s -> %s (type=%s)', source, mount_path, nas_type)

    try:
        print(cmd)
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
