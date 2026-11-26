import logging
import math
import time
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.crypto import salted_hmac

from authentication.mfa.radius_push import MFARadiusPush
from common.utils.lock import DistributedLock
from users.utils import MFABlockUtils

logger = logging.getLogger(__name__)
ACTIVE_STATUSES = {'queued', 'pending', 'approved'}
SEND_INTERVAL = 30


class RadiusPushAttempt:
    def __init__(self, key):
        self.key = key

    @classmethod
    def for_session(cls, session, user):
        expires_at = session.get('auth_password_expired_at')
        if not session.session_key or not session.get('auth_password') or not expires_at:
            return None
        if session.get('user_id') != str(user.pk) or expires_at <= time.time():
            return None
        binding = f'{session.session_key}:{user.pk}:{expires_at}'
        digest = salted_hmac('radius-push-login', binding).hexdigest()
        return cls(f'radius-push:{digest}')

    def get(self, attempt_id=None):
        attempt = cache.get(self.key)
        if not attempt or (attempt_id is not None and attempt['id'] != attempt_id):
            return None
        if attempt['status'] in ACTIVE_STATUSES and attempt['deadline'] <= time.time():
            return {**attempt, 'status': 'timed_out'}
        return attempt

    def _save(self, attempt, status):
        attempt = {**attempt, 'status': status}
        ttl = max(1, math.ceil(attempt['expires_at'] - time.time()))
        cache.set(self.key, attempt, ttl)
        return attempt

    def start(self, user, ip, expires_at):
        with DistributedLock(self.key, expire=10):
            attempt = self.get()
            if attempt and attempt['status'] in ACTIVE_STATUSES:
                return attempt, False
            deadline = min(expires_at, time.time() + int(settings.RADIUS_PUSH_TIMEOUT))
            if deadline <= time.time():
                return None, False
            if not cache.add(f'radius-push-send:{user.pk}', True, SEND_INTERVAL):
                return None, False
            attempt = {
                'id': uuid4().hex,
                'deadline': deadline,
                'expires_at': expires_at,
                'user_id': str(user.pk),
                'ip': ip,
            }
            return self._save(attempt, 'queued'), True

    def transition(self, attempt_id, expected, status):
        with DistributedLock(self.key, expire=10):
            attempt = self.get(attempt_id)
            if attempt and attempt['status'] in expected:
                return self._save(attempt, status)
        return None

    def cancel(self, attempt_id=None):
        return self.transition(attempt_id, ACTIVE_STATUSES, 'cancelled')

    def enqueue(self, user, ip, expires_at):
        from authentication.tasks import authenticate_radius_push

        attempt, created = self.start(user, ip, expires_at)
        if not attempt:
            return {'status': 'rate_limited'}
        if created:
            try:
                authenticate_radius_push.apply_async(
                    args=(self.key, attempt['id']),
                    expires=int(settings.RADIUS_PUSH_TIMEOUT), retry=False,
                )
            except Exception:
                logger.exception('Could not queue RADIUS push request')
                self.transition(attempt['id'], {'queued'}, 'failed')
                return {'status': 'failed'}
        return attempt

    def run(self, attempt_id):
        attempt = self.transition(attempt_id, {'queued'}, 'pending')
        if not attempt:
            return
        user = get_user_model().objects.filter(pk=attempt['user_id']).first()
        backend = MFARadiusPush.for_user(user)
        if backend is None or MFABlockUtils(user.username, attempt['ip']).is_block():
            self.transition(attempt_id, {'pending'}, 'failed')
            return
        remaining = attempt['deadline'] - time.time()
        current = self.get(attempt_id)
        if remaining <= 0 or not current or current['status'] != 'pending':
            return
        try:
            status = backend.send_push(remaining)
        except Exception:
            logger.exception('RADIUS push request failed')
            status = 'failed'
        with DistributedLock(self.key, expire=10):
            current = self.get(attempt_id)
            if not current or current['status'] != 'pending':
                return
            self._save(current, status)
            if status == 'rejected':
                MFABlockUtils(user.username, attempt['ip']).incr_failed_count()
