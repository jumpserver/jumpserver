#  coding: utf-8
#

from django.db.models import Q

from ..models import RemoteAppPermission


__all__ = [
    'RemoteAppPermissionUtil',
]


def get_user_remote_app_permissions(user, include_group=True):
    if include_group:
        groups = user.groups.all()
        arg = Q(users=user) | Q(user_groups__in=groups)
    else:
        arg = Q(users=user)
    return RemoteAppPermission.objects.all().valid().filter(arg)


def get_user_group_remote_app_permissions(user_group):
    return RemoteAppPermission.objects.all().valid().filter(
        user_groups=user_group
    )


class RemoteAppPermissionUtil:
    get_permissions_map = {
        "User": get_user_remote_app_permissions,
        "UserGroup": get_user_group_remote_app_permissions,
    }

    def __init__(self, obj):
        self.object = obj

    @property
    def permissions(self):
        obj_class = self.object.__class__.__name__
        func = self.get_permissions_map[obj_class]
        _permissions = func(self.object)
        return _permissions

    def get_remote_apps(self):
        remote_apps = set()
        for perm in self.permissions:
            remote_apps.update(list(perm.remote_apps.all()))
        return remote_apps
