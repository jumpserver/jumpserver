from django.contrib.sessions.middleware import SessionMiddleware as DjangoSessionMiddleware
from django.core.cache import cache
from django.utils import timezone
from django.utils.crypto import salted_hmac

from . import LOGIN_POLICY_KEY, policy_locked


class SessionMiddleware(DjangoSessionMiddleware):
    def process_response(self, request, response):
        session = getattr(request, 'session', None)
        renewal_key = None
        renewal = None
        if session is not None and response.status_code < 500:
            policy = session.login_policy
            timestamp = timezone.now().timestamp()
            if policy and session.get_expiry_date() <= timezone.now():
                # Another request may have renewed the login or cancelled its close deadline.
                policy = session.load().get(LOGIN_POLICY_KEY)
                if policy:
                    session._session_cache[LOGIN_POLICY_KEY] = policy
                else:
                    session.clear()
            if (
                policy and policy['renew'] and not policy_locked(policy)
                and not policy.get('pending_close') and response.status_code < 400
                and timestamp - policy['renewed_at'] >= 60
                and not request.path_info.startswith('/api/v1/authentication/user-session/')
                and not (request.method in ('GET', 'HEAD') and session.renewal_exclusions.match(request.path_info))
            ):
                renewal_key = 'web-session-renewal:' + salted_hmac('session-renewal', session.session_key).hexdigest()
                renewal = {**policy, 'renewed_at': timestamp, 'expires_at': timestamp + policy['duration']}
                if cache.add(renewal_key, renewal, timeout=60):
                    session[LOGIN_POLICY_KEY] = renewal
                else:
                    # Concurrent business writes must retain the winning request's deadline.
                    shared = cache.get(renewal_key)
                    if shared and shared['renewed_at'] > policy['renewed_at']:
                        session._session_cache[LOGIN_POLICY_KEY] = {
                            **policy, 'renewed_at': shared['renewed_at'], 'expires_at': shared['expires_at'],
                        }
                    renewal_key = None
        try:
            return super().process_response(request, response)
        except Exception:
            # A failed save must not suppress the next request's renewal attempt.
            if renewal_key and cache.get(renewal_key) == renewal:
                cache.delete(renewal_key)
            raise
