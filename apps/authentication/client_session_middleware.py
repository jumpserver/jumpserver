import logging

logger = logging.getLogger(__name__)


class ClientLoginSessionExpiryMiddleware:
    """Persist lazy expiry after a rejected API's ATOMIC_REQUESTS rollback."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        session_id = getattr(request, 'expired_client_login_session_id', None)
        if session_id:
            from authentication.services.client_login_session import validate_session
            try:
                validate_session(session_id, mutate=True)
            except Exception:
                # The read-only gate has already rejected access. Keep that response
                # even when persistence is unavailable; every retry checks time again.
                logger.exception('Unable to persist expired client login session %s', session_id)
        return response
