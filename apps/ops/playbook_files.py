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
    if (
        not isinstance(key, str)
        or any(char in key for char in ('\x00', '\\'))
        or os.path.isabs(key)
    ):
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


def _file_tree_node(root_path, file_path, is_directory):
    parent_key = os.path.relpath(file_path.parent, root_path)
    node = {
        'name': file_path.name,
        'title': file_path.name,
        'id': os.path.relpath(file_path, root_path),
        'isParent': is_directory,
        'open': is_directory,
        'pId': parent_key if parent_key != '.' else 'root',
        'temp': False,
    }
    if not is_directory:
        node['iconSkin'] = 'file'
    return node


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
        for name in [*dirs, *sorted(files)]:
            file_path = Path(path, name)
            if file_path.is_symlink():
                continue
            node = _file_tree_node(root_path, file_path, name in dirs)
            if node['isParent'] and expand_key == node['id']:
                node['open'] = True
            nodes.append(node)
    return nodes
