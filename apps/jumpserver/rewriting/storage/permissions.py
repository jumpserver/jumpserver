# ~*~ coding: utf-8 ~*~

from uuid import UUID

from django.conf import settings

path_perms_map = {
    'xpack': 'none',
    'settings': 'none',
    'img': 'none',
    'replay': 'terminal.view_sessionreplay',
    'applets': 'terminal.view_applet',
    'virtual_apps': 'terminal.view_virtualapp',
    'playbooks': 'ops.view_playbook',
    'images': 'default'
}


def allow_replay_access(private_file):
    from terminal.models import Session

    request = private_file.request
    if not request.user.is_authenticated or not request.user.has_perm('terminal.view_sessionreplay'):
        return False

    # Authorize the actual storage key, including split recordings and index files.
    parts = private_file.relative_name.split('/')
    if parts[0] == settings.VENDOR:
        parts = parts[1:]
    if len(parts) not in (3, 4) or parts[0] != 'replay':
        return False
    if any(not part or part in ('.', '..') or '\\' in part for part in parts):
        return False
    session_name = parts[2] if len(parts) == 4 else parts[2].split('.', 1)[0]
    try:
        session_id = UUID(session_name)
    except ValueError:
        return False

    # OrgManager must be invoked inside the current request's organization.
    session = Session.objects.filter(id=session_id).first()
    if session is None or parts[1] != session.date_start.strftime('%Y-%m-%d'):
        return False
    if len(parts) == 4:
        return parts[2] == str(session.id)
    suffixes = {*Session.SUFFIX_MAP.values(), '.gz', '.json', '.tar'}
    return parts[2] in {str(session.id) + suffix for suffix in suffixes}


def allow_access(private_file):
    request = private_file.request
    request_path = private_file.request.path
    path_list = str(request_path)[1:].split('/')
    path_base = path_list[1] if len(path_list) > 1 else None
    if path_base not in path_perms_map and len(path_list) > 2:
        vendor = path_list[1]
        if vendor == settings.VENDOR:
            path_base = path_list[2]
    path_perm = path_perms_map.get(path_base, None)

    if ".." in request_path:
        return False
    if not path_perm:
        return False
    if path_base == 'replay':
        return allow_replay_access(private_file)
    if path_perm == 'none' or request.user.has_perms([path_perm]):
        # 不需要权限检查，任何人都可以访问
        return True
    if path_perm == 'default':
        return request.user.is_authenticated and request.user.is_staff
    return False
