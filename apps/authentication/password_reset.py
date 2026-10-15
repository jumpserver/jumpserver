"""Session-bound password recovery, isolated from login and MFA challenges."""
import json
import math
import re
import secrets
import time
from contextlib import ExitStack, contextmanager

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.translation import gettext as _

from common.utils import get_logger, get_request_ip, random_string

logger = get_logger(__name__)
FLOW_TTL = 300
SEND_INTERVAL = 60
MAX_ATTEMPTS = 3


class RecoveryError(ValueError):
    pass


class RecoveryThrottled(RecoveryError):
    def __init__(self, wait):
        self.wait = max(1, math.ceil(wait))
        super().__init__(
            _('Too many requests. Try again in {seconds} seconds.').format(seconds=self.wait)
        )


def key(scope, *parts):
    digest = salted_hmac(
        'password-recovery', json.dumps(parts, ensure_ascii=False), algorithm='sha256'
    ).hexdigest()
    return 'password-recovery:{}:{}'.format(scope, digest)


def sms_enabled():
    return settings.XPACK_LICENSE_IS_VALID and settings.SMS_ENABLED


def validate_target(form_type, target):
    if not target:
        raise ValidationError(_('This field is required.'))
    if form_type == 'email':
        validate_email(target)
    elif form_type != 'sms' or not sms_enabled():
        raise ValidationError(_('This verification method is unavailable.'))
    elif not re.fullmatch(r'\+[0-9]{6,20}', target):
        raise ValidationError(_('Enter a valid phone number including the country code.'))


def increment(cache_key, timeout):
    # Both add and incr are atomic on the shared Redis cache.
    for _attempt in range(3):
        cache.add(cache_key, 0, timeout)
        try:
            return cache.incr(cache_key)
        except ValueError:
            continue
    raise RecoveryError(_('Service unavailable. Please try again later.'))


def limit(request, stage, username='', target=''):
    rules = [(get_request_ip(request), 30 if stage != 'send' else 10, 60, 'ip')]
    if username:
        rules.append((username.lower(), 5 if stage == 'send' else 10, FLOW_TTL, 'account'))
    if target:
        rules.append((target.lower(), 5, FLOW_TTL, 'target'))
    now = time.time()
    for identifier, maximum, window, dimension in rules:
        bucket = int(now // window)
        count = increment(key('limit', stage, dimension, identifier, bucket), window + 1)
        if count > maximum:
            raise RecoveryThrottled((bucket + 1) * window - now)


def issue(request, username):
    limit(request, 'issue')
    if not request.session.session_key:
        request.session.create()
    token = random_string(36)
    cache.set(key('flow', token), {
        'username': username, 'session': request.session.session_key,
        'expires': time.time() + FLOW_TTL,
    }, FLOW_TTL)
    return token


def get_flow(request, token):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9]{36}', token):
        return None
    flow = cache.get(key('flow', token))
    if (not flow or flow['session'] != request.session.session_key
            or flow['expires'] <= time.time()):
        return None
    return flow


def reserve_send(request, token, flow, form_type, target):
    from common.utils.lock import DistributedLock

    limit(request, 'send', flow['username'], target)
    # Apply the same cooldown to every submitted account and recipient, even if absent.
    cooldown_keys = [key('cooldown', dimension, identifier) for dimension, identifier in [
        ('account', flow['username'].lower()), ('target', target.lower()),
    ]]
    with ExitStack() as locks:
        # Stable ordering also serializes requests sharing just one of the dimensions.
        for cooldown_key in sorted(cooldown_keys):
            locks.enter_context(DistributedLock(key('send-lock', cooldown_key)))
        now = time.time()
        until = max(cache.get_many(cooldown_keys).values(), default=0)
        if until > now:
            raise RecoveryThrottled(until - now)
        request_id = random_string(36)
        try:
            cache.set_many({k: now + SEND_INTERVAL for k in cooldown_keys}, SEND_INTERVAL)
            cache.set(key('pending', token), {
                'id': request_id, 'form_type': form_type, 'target': key('target', target),
            }, max(1, math.ceil(flow['expires'] - now)))
        except Exception:
            cache.delete_many(cooldown_keys)
            raise
        return request_id


def matching_user(username, form_type, target):
    from authentication.utils import check_user_property_is_correct

    if form_type == 'sms' and not sms_enabled():
        return None
    user = check_user_property_is_correct(
        username, **{'phone' if form_type == 'sms' else 'email': target}
    )
    # The existing send-code API only permits local users to recover passwords.
    return user if user and user.is_local else None


def deliver_code(token, request_id, form_type, target):
    from common.tasks import send_mail_async
    from common.utils.verify_code import send_sms_async
    from settings.utils import get_login_title
    from users.serializers import SmsUserSerializer

    flow = cache.get(key('flow', token))
    pending = cache.get(key('pending', token))
    if (not flow or flow['expires'] <= time.time() or not pending
            or pending['id'] != request_id or pending['form_type'] != form_type
            or pending['target'] != key('target', target)):
        return
    if not cache.add(key('delivery', request_id), True, FLOW_TTL):
        return
    user = matching_user(flow['username'], form_type, target)
    if not user:
        return
    length = max(6, settings.SMS_CODE_LENGTH)
    code = ''.join(secrets.choice('0123456789') for _ in range(length))
    ttl = min(settings.VERIFY_CODE_TTL, math.ceil(flow['expires'] - time.time()))
    if ttl <= 0:
        return
    code_key = key('code', request_id)
    cache.set(code_key, {
        'digest': key('digest', request_id, code), 'user_id': str(user.id),
        'password_fingerprint': key('password', user.password),
    }, ttl)
    try:
        if form_type == 'sms':
            send_sms_async.apply_async(
                args=(target, code, SmsUserSerializer(user).data),
                argsrepr='(<redacted>)', priority=100,
            )
        else:
            subject = '%s: %s' % (get_login_title(), _('Forgot password'))
            message = render_to_string('authentication/_msg_reset_password_code.html', {
                'user': user, 'title': subject, 'code': code,
                'tip': _('The verification code is valid for {seconds} seconds.').format(seconds=ttl),
            })
            send_mail_async.apply_async(
                args=(subject, message, [target]), kwargs={'html_message': message},
                argsrepr='(<redacted>)', kwargsrepr='{<redacted>}', priority=100,
            )
    except Exception:
        cache.delete(code_key)
        # Do not put recipients, codes, or transport exception payloads in the log.
        logger.error('Unable to enqueue password recovery verification message')


def verify(request, token, flow, form_type, target, code):
    limit(request, 'verify', flow['username'])
    error = _('Verification failed. Check your information or get a new code.')
    pending = cache.get(key('pending', token))
    attempts = increment(key('attempts', token, (pending or {}).get('id')), FLOW_TTL)
    if attempts > MAX_ATTEMPTS or not pending:
        raise RecoveryError(error)
    record = cache.get(key('code', pending['id']))
    digest = key('digest', pending['id'], code)
    matches = constant_time_compare(digest, (record or {}).get('digest', '0' * 64))
    if (not record or not matches or pending['form_type'] != form_type
            or pending['target'] != key('target', target)):
        raise RecoveryError(error)
    if not cache.add(key('consumed', pending['id']), True, FLOW_TTL):
        raise RecoveryError(error)
    cache.delete(key('code', pending['id']))
    user = matching_user(flow['username'], form_type, target)
    if (not user or str(user.id) != record['user_id']
            or not constant_time_compare(
                key('password', user.password), record['password_fingerprint'])):
        raise RecoveryError(error)
    cache.delete(key('flow', token))
    cache.delete(key('pending', token))
    return user


@contextmanager
def reset_token_lock(token):
    from common.utils.lock import DistributedLock
    from users.models import User

    record = cache.get(User.CACHE_KEY_USER_RESET_PASSWORD_PREFIX.format(token)) or {}
    if not record.get('password_fingerprint'):
        yield False  # Administrative reset links and first-login flows retain their behavior.
        return
    # Renew while the database transaction is running; release on success or rollback.
    with DistributedLock(key('reset-lock', token)):
        yield True
