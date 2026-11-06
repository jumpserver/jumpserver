from django.db import transaction


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
