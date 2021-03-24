from rest_framework import permissions

from .utils import is_auth_password_time_valid


class IsAuthPasswdTimeValid(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        return super().has_permission(request, view) \
            and is_auth_password_time_valid(request.session)
