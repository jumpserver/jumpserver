from rest_framework import permissions

from rbac.builtin import BuiltinRole
from .utils import is_auth_password_time_valid


class IsAuthPasswdTimeValid(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        return super().has_permission(request, view) \
            and is_auth_password_time_valid(request.session)


class UserObjectPermission(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if view.action not in ['update', 'partial_update', 'destroy']:
            return True

        user = request.user
        if user.is_superuser:
            return True

        system_admin_id = BuiltinRole.system_admin.id
        return system_admin_id not in [
            str(r.id) for r in obj.system_roles.all()
        ]
