"""External certificate challenges with session binding and atomic single-use claims."""
import base64
import secrets
import time

from django.core.cache import cache
from rest_framework.throttling import AnonRateThrottle

from .configuration import REVISION, ensure_enabled, get_snapshot
from .exceptions import UKeyAuthError


class ChallengeThrottle(AnonRateThrottle):
    scope = 'ukey_challenge'
    rate = '20/min'


def session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def issue(request, purpose, target='', binding_version=''):
    snapshot = get_snapshot()
    provider = ensure_enabled(snapshot)
    if provider.binding_mode != 'certificate':
        raise UKeyAuthError('UKey configuration changed; refresh and retry')
    key = session_key(request)
    if not ChallengeThrottle().allow_request(request, None):
        raise UKeyAuthError('Too many UKey challenges; try again later')
    code = provider.generate_challenge()
    token = secrets.token_urlsafe(32)
    ttl = snapshot['AUTH_UKEY_CHALLENGE_TTL']
    record = {
        'session': key, 'purpose': purpose, 'target': str(target),
        'actor': str(request.user.pk) if request.user.is_authenticated else '',
        'provider': provider.id, 'revision': snapshot[REVISION], 'code': code,
        'expires': time.time() + ttl, 'binding_version': binding_version,
    }
    if get_snapshot()[REVISION] != snapshot[REVISION]:
        raise UKeyAuthError('UKey configuration changed; refresh and retry')
    cache.set('ukey:challenge:' + token, record, ttl)
    return {
        'id': token, 'code': code, 'code_base64': base64.b64encode(code.encode()).decode(),
        'length': len(code), 'revision': snapshot[REVISION], 'provider': provider.id,
    }


def consume(request, token, purpose, target=''):
    if not isinstance(token, str) or len(token) != 43:
        raise UKeyAuthError('Invalid or expired UKey challenge')
    record = cache.get('ukey:challenge:' + token)
    actor = str(request.user.pk) if request.user.is_authenticated else ''
    if (not record or record['session'] != request.session.session_key
            or record['purpose'] != purpose or record['target'] != str(target)
            or record['actor'] != actor or record['expires'] <= time.time()):
        raise UKeyAuthError('Invalid or expired UKey challenge')
    snapshot = get_snapshot()
    ensure_enabled(snapshot, record['provider'])
    if snapshot[REVISION] != record['revision']:
        raise UKeyAuthError('UKey configuration changed; refresh and retry')
    # Redis SET NX (Django cache.add) is atomic across workers. Keep the marker
    # longer than the maximum challenge TTL; never release it on verification failure.
    if not cache.add('ukey:consumed:' + token, True, timeout=3601):
        raise UKeyAuthError('UKey challenge has already been used')
    cache.delete('ukey:challenge:' + token)
    return record, snapshot
