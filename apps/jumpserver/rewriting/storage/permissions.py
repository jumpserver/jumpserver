# ~*~ coding: utf-8 ~*~

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
    if path_perm == 'none' or request.user.has_perms([path_perm]):
        # 不需要权限检查，任何人都可以访问
        return True
    if path_perm == 'default':
        return request.user.is_authenticated and request.user.is_staff
    return False
