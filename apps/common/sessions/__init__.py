import json
import re
from contextlib import nullcontext
from datetime import datetime, timezone as datetime_timezone
from importlib import import_module
from math import ceil

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.core.cache import caches
from django.utils import timezone
from django.utils.crypto import salted_hmac

from common.utils.lock import DistributedLock

LOGIN_POLICY_KEY = '_jms_login_policy'
PAGE_CLOSE_GRACE_SECONDS = 10


def closed_pages_locked(policy):
    return bool(policy and policy.get('close_lock_at', float('inf')) <= timezone.now().timestamp())


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
        if (policy and min(policy['expires_at'], policy.get('closing_at', policy['expires_at']))
                <= timezone.now().timestamp()):
            self._session_key = None
            return {}
        return data

    async def aload(self):
        return await sync_to_async(self.load)()

    def start_login(self, policy=None, expires_at=None):
        policy = dict(web_login_policy() if policy is None else policy)
        timestamp = timezone.now().timestamp()
        policy['expires_at'] = expires_at.timestamp() if expires_at else timestamp + policy['duration']
        policy['renewed_at'] = min(timestamp, policy['expires_at'] - policy['duration'])
        policy['authenticated_at'] = None if expires_at else timestamp
        self[LOGIN_POLICY_KEY] = policy
        self._new_login_policy = True

    def ensure_login_policy(self):
        if self.get('_auth_user_id') and not self.login_policy:
            # Adopt an existing login without granting it a fresh full lifetime.
            self.start_login(expires_at=session_expiry(self.session_key) if self.session_key else None)

    def get_expiry_date(self, **kwargs):
        if policy := self.login_policy:
            expires_at = min(policy['expires_at'], policy.get('closing_at', policy['expires_at']))
            return datetime.fromtimestamp(expires_at, tz=datetime_timezone.utc)
        return super().get_expiry_date(**kwargs)

    def update_page(self, page_id, entering, *, lock_on_close=False):
        self.ensure_login_policy()
        if not self.login_policy:
            return
        self._page_action = page_id, entering, lock_on_close
        self.save()
        # Already saved under the session lock; the response middleware need not save it again.
        self.modified = False

    def clear_close_lock(self):
        # Only a verified unlock may clear a close deadline that has already passed.
        self._clear_close_lock = True
        self.save()
        self.modified = False

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

    def save(self, *args, **kwargs):
        self.ensure_login_policy()
        existing_login = self.login_policy and self.session_key and not kwargs.get('must_create')
        lock = nullcontext()
        if existing_login:
            lock = DistributedLock(
                'web-session-save:' + salted_hmac('session-save', self.session_key).hexdigest(),
                expire=10,
            )
        with lock:
            if existing_login:
                # Serialize page membership and ordinary session writes, for either Session backend.
                stored = super().load().get(LOGIN_POLICY_KEY)
                if self.session_key is None:
                    raise UpdateError('The login has expired.')
                if stored and not getattr(self, '_new_login_policy', False):
                    policy = dict(self.login_policy)
                    if stored['renewed_at'] > policy['renewed_at']:
                        policy.update(renewed_at=stored['renewed_at'], expires_at=stored['expires_at'])
                    for name in ('closing_at', 'close_lock_at', 'pages', 'closed_pages'):
                        policy.pop(name, None)
                        if name in stored:
                            policy[name] = stored[name]
                    self._session_cache[LOGIN_POLICY_KEY] = policy
            if self.login_policy and self.get_expiry_date() <= timezone.now():
                raise UpdateError('The login has expired.')
            if getattr(self, '_clear_close_lock', False) and self.login_policy:
                self._session_cache[LOGIN_POLICY_KEY].pop('close_lock_at', None)
            if action := getattr(self, '_page_action', None):
                page_id, entering, lock_on_close = action
                policy = dict(self.login_policy)
                pages = set(policy.get('pages', ()))
                closed = list(policy.get('closed_pages', ()))
                if page_id not in closed:
                    if entering:
                        pages.add(page_id)
                        policy.pop('closing_at', None)
                        if not closed_pages_locked(policy):
                            policy.pop('close_lock_at', None)
                    else:
                        pages.discard(page_id)
                        closed.append(page_id)
                        if not pages and (policy['browser_close'] or lock_on_close):
                            deadline = 'closing_at' if policy['browser_close'] else 'close_lock_at'
                            policy[deadline] = min(policy.get(deadline, float('inf')),
                                                   timezone.now().timestamp() + PAGE_CLOSE_GRACE_SECONDS)
                # ponytail: retain 128 closed IDs for reordered delivery, not crash detection.
                # A leased presence registry is the upgrade path if crash detection is required.
                policy.update(pages=sorted(pages), closed_pages=closed[-128:])
                self._session_cache[LOGIN_POLICY_KEY] = policy
            result = super().save(*args, **kwargs)
            self._new_login_policy = False
            self._page_action = None
            self._clear_close_lock = False
            return result

    async def asave(self, *args, **kwargs):
        return await sync_to_async(self.save)(*args, **kwargs)


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
        records = store_class.get_model_class().objects.filter(session_key__in=session_keys)
        return {record.session_key: record.get_decoded().get(LOGIN_POLICY_KEY) for record in records}
    keys = {key: store_class(session_key=key).cache_key for key in session_keys}
    data = caches[settings.SESSION_CACHE_ALIAS].get_many(keys.values())
    return {key: data.get(cache_key, {}).get(LOGIN_POLICY_KEY) for key, cache_key in keys.items()}
