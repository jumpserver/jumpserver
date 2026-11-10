import json
import re
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone as datetime_timezone
from importlib import import_module
from math import ceil, isfinite

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.core.cache import caches
from django.utils import timezone
from django.utils.crypto import salted_hmac

from common.utils.lock import DistributedLock

LOGIN_POLICY_KEY = '_jms_login_policy'
PAGE_CLOSE_GRACE_SECONDS = 10


class SessionStateConflict(Exception):
    pass


def valid_login_policy(policy):
    """Only the current, complete login state may retain authentication."""
    def timestamp(value):
        # Keep timestamps representable by datetime (before year 10000).
        return type(value) in (int, float) and 0 < value < 253402300800 and isfinite(value)

    if not isinstance(policy, dict) or {'closing_at', 'close_lock_at'} & policy.keys():
        return False
    if any(type(policy.get(name)) is not bool for name in ('locked', 'renew', 'browser_close')):
        return False
    if any(type(policy.get(name)) is not int or policy[name] < minimum for name, minimum in (
        ('duration', 1), ('state_version', 0), ('lock_password_failures', 0),
    )):
        return False
    if not all(timestamp(policy.get(name)) for name in ('authenticated_at', 'expires_at', 'renewed_at')):
        return False
    pending = policy.get('pending_close')
    if pending is not None and not (
        isinstance(pending, dict) and pending.get('action') in ('lock', 'logout') and timestamp(pending.get('at'))
    ):
        return False
    if policy.get('unlocked_at') is not None and not timestamp(policy['unlocked_at']):
        return False
    return all(isinstance(policy[name], list) and all(isinstance(page, str) for page in policy[name])
               for name in ('pages', 'closed_pages') if name in policy)


def normalize_security_state(policy):
    """A due close action is deterministic, including before its next persisted write."""
    policy = dict(policy)
    pending = policy.get('pending_close')
    if pending and pending['action'] == 'lock' and pending['at'] <= timezone.now().timestamp():
        policy['locked'] = True
        policy['state_version'] += 1
        policy.pop('pending_close')
    return policy


def policy_expiry(policy):
    pending = policy.get('pending_close')
    close_at = pending['at'] if pending and pending['action'] == 'logout' else float('inf')
    return min(policy['expires_at'], close_at)


def policy_locked(policy):
    return normalize_security_state(policy)['locked'] if policy else False


def _session_lock(session_key, *, renew=False):
    return DistributedLock(
        'web-session-save:' + salted_hmac('session-save', session_key).hexdigest(),
        expire=None if renew else 10, reentrant=True,
    )


def web_login_policy():
    # Read once at login so a worker's settings subscription cannot lag behind a save.
    from settings.models import Setting

    names = ('SESSION_COOKIE_AGE', 'SESSION_RENEW_ON_REQUEST', 'SESSION_EXPIRE_AT_BROWSER_CLOSE')
    values = {
        name: json.loads(value) for name, value in Setting.objects.filter(
            name__in=(*names, 'SESSION_SAVE_EVERY_REQUEST'),
        ).values_list('name', 'value')
    }
    explicit_renewal = None
    config = getattr(settings, 'CONFIG', None)
    if config is not None:
        explicit_renewal = config.get_from_config('SESSION_RENEW_ON_REQUEST')
        if explicit_renewal is None:
            explicit_renewal = config.get_from_env('SESSION_RENEW_ON_REQUEST')
        if explicit_renewal is not None:
            explicit_renewal = config.convert_type('SESSION_RENEW_ON_REQUEST', explicit_renewal)
    return {
        'duration': values.get('SESSION_COOKIE_AGE', settings.SESSION_COOKIE_AGE),
        'renew': values.get('SESSION_RENEW_ON_REQUEST', explicit_renewal if explicit_renewal is not None else
                           values.get('SESSION_SAVE_EVERY_REQUEST', settings.SESSION_RENEW_ON_REQUEST)),
        'browser_close': values.get('SESSION_EXPIRE_AT_BROWSER_CLOSE', settings.SESSION_EXPIRE_AT_BROWSER_CLOSE),
    }


class SessionSaveMixin:
    renewal_exclusions = re.compile(
        r'^/api/v1/(?:users/profile/|authentication/user-session/|authentication/web-session/status/)'
    )

    @property
    def login_policy(self):
        return self.get(LOGIN_POLICY_KEY)

    def load(self):
        data = super().load()
        policy = data.get(LOGIN_POLICY_KEY)
        if (data.get('_auth_user_id') or policy is not None) and (
            not valid_login_policy(policy) or policy_expiry(policy) <= timezone.now().timestamp()
        ):
            self._session_key = None
            return {}
        if policy:
            data[LOGIN_POLICY_KEY] = normalize_security_state(policy)
        return data

    async def aload(self):
        return await sync_to_async(self.load)()

    def start_login(self, policy=None):
        policy = dict(web_login_policy() if policy is None else policy)
        timestamp = timezone.now().timestamp()
        policy['expires_at'] = timestamp + policy['duration']
        policy['renewed_at'] = timestamp
        policy['authenticated_at'] = timestamp
        policy.update(locked=False, state_version=0, lock_password_failures=0)
        self[LOGIN_POLICY_KEY] = policy

    def get_expiry_date(self, **kwargs):
        if policy := self.login_policy:
            expires_at = policy_expiry(policy)
            return datetime.fromtimestamp(expires_at, tz=datetime_timezone.utc)
        return super().get_expiry_date(**kwargs)

    def update_page(self, page_id, entering, *, lock_on_close=False):
        if not self.login_policy:
            return
        self._page_action = page_id, entering, lock_on_close
        self.save()
        # Already saved under the session lock; the response middleware need not save it again.
        self.modified = False

    @contextmanager
    def control(self):
        """Serialize security mutations with page changes, ordinary saves and logout."""
        key = self.session_key
        if not key:
            raise UpdateError('The login has expired.')
        with _session_lock(key, renew=True):
            pending_data = dict(self._session_cache) if self.modified and hasattr(self, '_session_cache') else None
            data = self.load()
            self._session_cache = data
            if not data.get('_auth_user_id') or self.session_key is None:
                raise UpdateError('The login has expired.')
            if pending_data is not None:
                # Login middleware may just have completed MFA/SSO in this request.
                # Retain its additions/removals, but always take security state from storage.
                pending_data.pop(LOGIN_POLICY_KEY, None)
                if LOGIN_POLICY_KEY in data:
                    pending_data[LOGIN_POLICY_KEY] = data[LOGIN_POLICY_KEY]
                self._session_cache = pending_data
            yield

    def set_locked(self, locked, expected_version):
        self._lock_action = locked, expected_version
        try:
            self.save()
            self.modified = False
        finally:
            self._lock_action = None

    def record_lock_password_failure(self, expected_version):
        self._lock_failure_version = expected_version
        try:
            self.save()
            self.modified = False
            return self.login_policy['lock_password_failures']
        finally:
            self._lock_failure_version = None

    async def aget_expiry_date(self, **kwargs):
        return await sync_to_async(self.get_expiry_date)(**kwargs)

    def get_expiry_age(self, **kwargs):
        if self.login_policy:
            modification = kwargs.get('modification') or timezone.now()
            return max(0, ceil((self.get_expiry_date() - modification).total_seconds()))
        return super().get_expiry_age(**kwargs)

    async def aget_expiry_age(self, **kwargs):
        return await sync_to_async(self.get_expiry_age)(**kwargs)

    def get_expire_at_browser_close(self):
        if policy := self.login_policy:
            return policy['browser_close']
        return super().get_expire_at_browser_close()

    async def aget_expire_at_browser_close(self):
        return await sync_to_async(self.get_expire_at_browser_close)()

    def save(self, must_create=False):
        if (self.get('_auth_user_id') or self.login_policy is not None) and not valid_login_policy(self.login_policy):
            raise UpdateError('The login has expired.')
        key = self.session_key
        existing_session = key and not must_create
        lock = _session_lock(key) if existing_session else nullcontext()
        with lock:
            if existing_session:
                # Saves and deletion share the lock so a pending write cannot undo logout.
                data = super().load()
                stored = data.get(LOGIN_POLICY_KEY)
                if (data.get('_auth_user_id') or stored is not None) and not valid_login_policy(stored):
                    raise UpdateError('The login has expired.')
                if stored:
                    stored = normalize_security_state(stored)
                if self.session_key is None:
                    self._session_key = key
                    raise UpdateError('The login has expired.')
                if stored and self.login_policy:
                    policy = normalize_security_state(self.login_policy)
                    # An earlier response must not extend a login that is now locked.
                    if stored['locked'] or stored['renewed_at'] > policy['renewed_at']:
                        policy.update(renewed_at=stored['renewed_at'], expires_at=stored['expires_at'])
                    for name in ('locked', 'state_version', 'lock_password_failures', 'unlocked_at',
                                 'pending_close', 'pages', 'closed_pages'):
                        policy.pop(name, None)
                        if name in stored:
                            policy[name] = stored[name]
                    self._session_cache[LOGIN_POLICY_KEY] = policy
            if self.login_policy and self.get_expiry_date() <= timezone.now():
                raise UpdateError('The login has expired.')
            if self.login_policy:
                policy = normalize_security_state(self.login_policy)
                self._session_cache[LOGIN_POLICY_KEY] = policy
                if lock_action := getattr(self, '_lock_action', None):
                    locked, expected_version = lock_action
                    if expected_version != policy['state_version']:
                        raise SessionStateConflict()
                    if not locked:
                        policy['lock_password_failures'] = 0
                    pending = policy.get('pending_close')
                    if policy['locked'] != locked or (pending and pending['action'] == 'lock'):
                        policy['locked'] = locked
                        policy['state_version'] += 1
                        if not locked:
                            policy['unlocked_at'] = timezone.now().timestamp()
                        if pending and pending['action'] == 'lock':
                            policy.pop('pending_close')
                failure_version = getattr(self, '_lock_failure_version', None)
                if failure_version is not None:
                    from authentication.services.lock_password import MAX_LOCK_PASSWORD_FAILURES

                    if failure_version != policy['state_version'] or not policy['locked']:
                        raise SessionStateConflict()
                    # Apply increments only after merging the latest state under the session lock.
                    policy['lock_password_failures'] = min(
                        policy['lock_password_failures'] + 1, MAX_LOCK_PASSWORD_FAILURES,
                    )
                if action := getattr(self, '_page_action', None):
                    page_id, entering, lock_on_close = action
                    pages = set(policy.get('pages', ()))
                    closed = list(policy.get('closed_pages', ()))
                    if page_id not in closed:
                        if entering:
                            pages.add(page_id)
                            if policy.pop('pending_close', None):
                                policy['state_version'] += 1
                        else:
                            pages.discard(page_id)
                            closed.append(page_id)
                            if not pages and (policy['browser_close'] or lock_on_close):
                                if not policy.get('pending_close'):
                                    policy['pending_close'] = {
                                        'action': 'logout' if policy['browser_close'] else 'lock',
                                        'at': timezone.now().timestamp() + PAGE_CLOSE_GRACE_SECONDS,
                                    }
                                    policy['state_version'] += 1
                    # ponytail: retain 128 closed IDs for reordered delivery, not crash detection.
                    # A leased presence registry is the upgrade path if crash detection is required.
                    policy.update(pages=sorted(pages), closed_pages=closed[-128:])
            result = super().save(must_create=must_create)
            self._page_action = None
            return result

    async def asave(self, *args, **kwargs):
        return await sync_to_async(self.save)(*args, **kwargs)

    def delete(self, session_key=None):
        key = self.session_key if session_key is None else session_key
        if key is None:
            return
        with _session_lock(key):
            return super().delete(key)

    async def adelete(self, session_key=None):
        return await sync_to_async(self.delete)(session_key)


def session_expiry(session_key):
    """Read the actual stored deadline for either supported Session backend."""
    store_class = import_module(settings.SESSION_ENGINE).SessionStore
    if hasattr(store_class, 'get_model_class'):
        return store_class.get_model_class().objects.filter(session_key=session_key).values_list('expire_date', flat=True).first()
    from datetime import timedelta
    store = store_class(session_key=session_key)
    ttl = caches[settings.SESSION_CACHE_ALIAS].pttl(store.cache_key)
    return timezone.now() + timedelta(milliseconds=ttl) if ttl is not None and ttl >= 0 else None


def session_login_policies(session_keys):
    """Read only login policy metadata, in one query or cache batch for an online-device page."""
    if not session_keys:
        return {}
    store_class = import_module(settings.SESSION_ENGINE).SessionStore
    if hasattr(store_class, 'get_model_class'):
        records = store_class.get_model_class().objects.filter(session_key__in=session_keys, expire_date__gt=timezone.now())
        sessions = {record.session_key: record.get_decoded() for record in records}
    else:
        keys = {key: store_class(session_key=key).cache_key for key in session_keys}
        data = caches[settings.SESSION_CACHE_ALIAS].get_many(keys.values())
        sessions = {key: data.get(cache_key, {}) for key, cache_key in keys.items()}
    timestamp = timezone.now().timestamp()
    return {
        key: normalize_security_state(policy) for key, data in sessions.items()
        if data.get('_auth_user_id') and valid_login_policy(policy := data.get(LOGIN_POLICY_KEY))
        and policy_expiry(policy) > timestamp
    }
