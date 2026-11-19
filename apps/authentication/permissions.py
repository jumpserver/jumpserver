import time

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions

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
        confirm_user_id = session.get('CONFIRM_USER_ID')
        if not request.user.is_authenticated or \
                confirm_user_id != str(request.user.pk):
            for key in ('CONFIRM_LEVEL', 'CONFIRM_TYPE', 'CONFIRM_TIME', 'CONFIRM_USER_ID'):
                session.pop(key, None)
            if confirm_user_id:
                raise self.confirmation_required(
                    'user_mismatch', _('The confirmation belongs to a different user.'),
                )
            raise self.confirmation_required(
                'missing_confirmation', _('No identity confirmation was found in the current session.'),
            )
        confirm_level = session.get('CONFIRM_LEVEL')
        confirm_type = session.get('CONFIRM_TYPE')
        confirm_time = session.get('CONFIRM_TIME')

        ttl = self.get_ttl(confirm_type)
        now = int(time.time())

        if not confirm_level or not confirm_time:
            raise self.confirmation_required(
                'missing_confirmation', _('No identity confirmation was found in the current session.'),
            )

        if confirm_level < self.min_level:
            raise self.confirmation_required(
                'insufficient_confirmation', _('The current confirmation does not meet the required level.'),
            )
        if confirm_time <= now - ttl:
            raise self.confirmation_required(
                'confirmation_expired',
                _('The identity confirmation has expired (valid for %(ttl)s seconds).') % {'ttl': ttl},
            )
        return True

    def confirmation_required(self, reason, message):
        ttl = self.get_ttl(self.min_type)
        instructions = _(
            'Confirm the current user with %(confirm_type)s, then retry with the same session cookie. '
            'This confirmation is valid for %(ttl)s seconds while the session remains valid.'
        ) % {'confirm_type': self.min_type, 'ttl': ttl}
        error = UserConfirmRequired(
            code=self.min_type, detail=f'{message} {instructions}', reason=reason, confirm_ttl=ttl,
        )
        error.detail['confirm_url'] = reverse('api-auth:confirm-list')
        return error

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
        if super().has_permission(request, view):
            return True
        # Connection tokens are bootstrap capabilities, not a user session.
        if request.method not in permissions.SAFE_METHODS:
            return False
        return self.is_valid_connection_token(request)

    @staticmethod
    def is_valid_connection_token(request):
        token_id = request.query_params.get('token')
        if not token_id:
            return False
        with tmp_to_root_org():
            token = get_object_or_none(ConnectionToken, id=token_id)
        return token and token.is_valid()
