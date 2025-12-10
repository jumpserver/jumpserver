import time
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from authentication.const import ConfirmType
from authentication.models import ConnectionToken
from common.exceptions import UserConfirmRequired
from common.permissions import IsValidUser
from common.utils import get_object_or_none
from orgs.utils import tmp_to_root_org


class UserConfirmation(permissions.BasePermission):
    ttl = 60 * 5
    min_level = 1
    min_type = 'relogin'

    def has_permission(self, request, view):
        if not settings.SECURITY_VIEW_AUTH_NEED_MFA:
            return True

        session = getattr(request, 'session', {})
        confirm_level = session.get('CONFIRM_LEVEL')
        confirm_type = session.get('CONFIRM_TYPE')
        confirm_time = session.get('CONFIRM_TIME')

        ttl = self.get_ttl(confirm_type)
        now = int(time.time())

        if not confirm_level or not confirm_time:
            raise UserConfirmRequired(code=self.min_type)

        if confirm_level < self.min_level or \
                confirm_time < now - ttl:
            raise UserConfirmRequired(code=self.min_type)
        return True

    def get_ttl(self, confirm_type):
        if confirm_type == ConfirmType.MFA:
            ttl = settings.SECURITY_MFA_VERIFY_TTL
        else:
            ttl = self.ttl
        return ttl

    @classmethod
    def require(cls, confirm_type=ConfirmType.RELOGIN, ttl=60 * 5):
        min_level = ConfirmType.values.index(confirm_type) + 1
        name = 'UserConfirmationLevel{}TTL{}'.format(min_level, ttl)
        return type(name, (cls,), {'min_level': min_level, 'ttl': ttl, 'min_type': confirm_type})


class IsValidUserOrConnectionToken(IsValidUser):
    def has_permission(self, request, view):
        if self.is_valid_connection_token(request):
            return True

        if not (request.user and request.user.is_valid):
            error = _('No user or invalid user')
            raise PermissionDenied(error)

        return super().has_permission(request, view)

    @staticmethod
    def is_valid_connection_token(request):
        token_id = request.query_params.get('token')
        if not token_id:
            return False
        with tmp_to_root_org():
            token = get_object_or_none(ConnectionToken, id=token_id)
        return token and token.is_valid()
