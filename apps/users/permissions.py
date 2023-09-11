from rest_framework import permissions

from .utils import is_auth_password_time_valid


class IsAuthPasswdTimeValid(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        return super().has_permission(request, view) \
            and is_auth_password_time_valid(request.session)


class UserObjectPermission(permissions.IsAuthenticated):

    def has_object_permission(self, request, view, obj):
        if view.action not in ['update', 'partial_update', 'destroy']:
            return True

        if not request.user.is_superuser and obj.is_superuser:
            return False

        return True
