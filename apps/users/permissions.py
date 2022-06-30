from rest_framework import permissions

from common.permissions import UserConfirmation
from common.exceptions import UserConfirmRequired
from .utils import is_auth_password_time_valid


class IsAuthPasswdTimeValid(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        return super().has_permission(request, view) \
               and is_auth_password_time_valid(request.session)


class IsAuthConfirmTimeValid(UserConfirmation.require(1)):

    def has_permission(self, request, view):
        try:
            return super().has_permission(request, view)
        except UserConfirmRequired:
            return False
