import time

from django.db import transaction
from rest_framework.permissions import BasePermission
from rest_framework.throttling import UserRateThrottle

from common.exceptions import UserConfirmRequired

LOCK_PASSWORD_PURPOSE = 'lock_password'
LOCK_PASSWORD_PROOF = 'lock_password_confirmation'


class LockPasswordConfirmationThrottle(UserRateThrottle):
    scope = 'lock_password_confirmation'
    rate = '5/minute'


def confirmation_type(user):
    return 'password' if user.source == user.Source.local else 'mfa'


def mark_lock_password_confirmation(request, method):
    if method == confirmation_type(request.user):
        request.session[LOCK_PASSWORD_PROOF] = {
            'user': str(request.user.pk), 'method': method, 'at': time.time(),
        }


class LockPasswordConfirmation(BasePermission):
    def has_permission(self, request, view):
        proof = request.session.get(LOCK_PASSWORD_PROOF, {})
        method = confirmation_type(request.user)
        when = proof.get('at') if isinstance(proof, dict) else None
        if (isinstance(when, (int, float)) and 0 <= time.time() - when <= 300
                and proof.get('user') == str(request.user.pk) and proof.get('method') == method):
            return True
        error = UserConfirmRequired(code=method)
        error.detail['purpose'] = LOCK_PASSWORD_PURPOSE
        raise error


MAX_LOCK_PASSWORD_FAILURES = 5
LOCK_PASSWORD_LOGOUT_CODE = 'lock_password_attempts_exceeded'


def record_lock_password_failure(session):
    # Serialize attempts from different tabs/workers; release the row before revoking.
    queryset = type(session).objects.filter(pk=session.pk)
    with transaction.atomic():
        current = queryset.select_for_update().values_list('lock_password_failures', flat=True).first()
        if current is None:
            return MAX_LOCK_PASSWORD_FAILURES
        failures = min(current + 1, MAX_LOCK_PASSWORD_FAILURES)
        queryset.update(lock_password_failures=failures)
        return failures
