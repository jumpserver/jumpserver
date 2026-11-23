from rest_framework import permissions

from .utils import is_auth_password_time_valid


class IsAuthPasswdTimeValid(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        return super().has_permission(request, view) \
            and is_auth_password_time_valid(request.session)


class CanManageUser(permissions.IsAuthenticated):

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser or not obj.is_superuser


class UserObjectPermission(CanManageUser):

    def has_object_permission(self, request, view, obj):
        if view.action in (
            'update', 'partial_update', 'bulk_update', 'partial_bulk_update',
            'destroy', 'bulk_destroy',
        ):
            return super().has_object_permission(request, view, obj)
        return True
