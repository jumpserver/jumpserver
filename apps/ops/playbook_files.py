import os
import stat
from pathlib import Path

from django.core.exceptions import SuspiciousFileOperation
from django.utils._os import safe_join
from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException
from common.utils.yml import atomic_dump_text


def _invalid_file_path():
    return JMSException(code='invalid_file_path', detail={'msg': _('Invalid file path')})


def resolve_playbook_path(work_path, key, *, allow_root=False):
    if not isinstance(key, str) or any(char in key for char in ('\x00', '\\')) or os.path.isabs(key):
        raise _invalid_file_path()
    key = '' if key == 'root' else key.removeprefix('root/')
    root = Path(os.path.abspath(work_path))
    try:
        path = Path(safe_join(root, key))
    except (SuspiciousFileOperation, ValueError) as exc:
        raise _invalid_file_path() from exc
    if path == root and not allow_root:
        raise _invalid_file_path()

    # safe_join checks lexical containment; filesystem links need a separate check.
    current = root
    for part in ('', *path.relative_to(root).parts):
        current = current / part
        if current.is_symlink():
            raise _invalid_file_path()
    return path


def validate_playbook_file_name(name):
    if name in {'.', '..', 'root'} or any(char in name for char in ('/', '\\', '\x00')):
        raise _invalid_file_path()


def write_playbook_file(path, content):
    mode = stat.S_IMODE(path.stat(follow_symlinks=False).st_mode) if path.exists() else None

    def write(stream):
        stream.write(content)
        if mode is not None:
            os.fchmod(stream.fileno(), mode)

    atomic_dump_text(path, write)


def generate_playbook_tree(playbook, root_path, expand_key=None):
    nodes = [
        {
            'name': playbook.name,
            'title': playbook.name,
            'id': 'root',
            'isParent': True,
            'open': True,
            'pId': '',
            'temp': False,
        }
    ]
    for path, dirs, files in os.walk(root_path):
        dirs[:] = sorted(name for name in dirs if not Path(path, name).is_symlink())
        relative_path = os.path.relpath(path, root_path)
        for name in [*dirs, *sorted(files)]:
            if Path(path, name).is_symlink():
                continue
            file_id = os.path.relpath(os.path.join(path, name), root_path)
            is_directory = name in dirs
            node = {
                'name': name,
                'title': name,
                'id': file_id,
                'isParent': is_directory,
                'open': is_directory,
                'pId': relative_path if relative_path != '.' else 'root',
                'temp': False,
            }
            if is_directory and expand_key == file_id:
                node['open'] = True
            if not is_directory:
                node['iconSkin'] = 'file'
            nodes.append(node)
    return nodes
