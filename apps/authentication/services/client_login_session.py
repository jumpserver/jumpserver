from contextlib import contextmanager
from datetime import timedelta
import hashlib

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.crypto import constant_time_compare
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from oauth2_provider.models import (
    get_access_token_model, get_application_model, get_grant_model, get_refresh_token_model,
)
from rest_framework.exceptions import AuthenticationFailed

from common.utils.lock import DistributedLock
from authentication.models.client_login_session import ClientLoginSession


POLICY_FIELDS = (
    'SECURITY_CLIENT_REAUTH_ON_EXIT',
    'SECURITY_CLIENT_IDLE_LOCK_TIME',
    'SECURITY_CLIENT_MAX_SESSION_TIME',
)
CLIENT_ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60
CLIENT_SESSION_RECEIPT_SALT = 'authentication.client-login-session-receipt'


class ClientSessionExpired(AuthenticationFailed):
    default_detail = _('Client login session expired. Please authenticate again.')
    default_code = 'client_session_expired'

    def __init__(self, session=None):
        super().__init__()
        self.session_id = session.pk if session else None
        self.client_login_reason = getattr(session, 'client_login_reason', None) or 'unknown'
        self.client_login_session = client_login_session_data(session) if session else None


def client_session_deadline(session):
    deadlines = [(value, reason) for value, reason in (
        (session.expires_at, 'absolute_timeout'), (session.policy_expires_at, 'policy_changed'),
    ) if value is not None]
    return min(deadlines, key=lambda item: item[0]) if deadlines else (None, None)


def client_login_session_data(session):
    """Serialize the already validated session without another policy/session query."""
    deadline, reason = client_session_deadline(session)
    return {
        'authenticated_at': session.authenticated_at.isoformat(),
        'expires_at': session.expires_at.isoformat() if session.expires_at else None,
        'policy_expires_at': session.policy_expires_at.isoformat() if session.policy_expires_at else None,
        'effective_expires_at': deadline.isoformat() if deadline else None,
        'expiry_reason': reason,
        'server_time': timezone.now().isoformat(),
    }


def client_session_receipt(application_id, token_family, token):
    """Bind a reason-only receipt to the exact issued credentials, never authorize it."""
    return signing.dumps({
        'application': str(application_id), 'family': str(token_family),
        'access_token': hashlib.sha256(token['access_token'].encode()).hexdigest(),
        'refresh_token': hashlib.sha256(token['refresh_token'].encode()).hexdigest(),
    }, salt=CLIENT_SESSION_RECEIPT_SALT, compress=True)


def expired_session_from_receipt(receipt, credential, token_type, *, client_id=None):
    """Explain failed authentication even after token cleanup; never accept the receipt as auth."""
    if (not isinstance(receipt, str) or len(receipt) > 2048 or not credential
            or token_type not in ('access_token', 'refresh_token')):
        return None
    try:
        payload = signing.loads(receipt, salt=CLIENT_SESSION_RECEIPT_SALT)
    except (signing.BadSignature, TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or not all(isinstance(payload.get(key), str)
                                              for key in ('application', 'family', token_type)):
        return None
    if not constant_time_compare(payload[token_type], hashlib.sha256(credential.encode()).hexdigest()):
        return None
    queryset = ClientLoginSession.objects.select_related('user').filter(application__in=client_applications())
    if client_id is not None:
        queryset = queryset.filter(application__client_id=client_id)
    try:
        session = queryset.filter(application_id=payload['application'], token_family=payload['family']).first()
    except (ValidationError, ValueError, TypeError):
        return None
    if session and not _session_is_valid(session, client_login_policy(), timezone.now()):
        return session
    return None


def client_login_policy():
    # Settings broadcasts update worker memory asynchronously. Read the three
    # authoritative values here so policy changes never have a stale-worker gap.
    from settings.models import Setting

    values = {name: getattr(settings, name, False if index == 0 else 0)
              for index, name in enumerate(POLICY_FIELDS)}
    for item in Setting.objects.filter(name__in=POLICY_FIELDS):
        values[item.name] = item.cleaned_value
    return {
        'reauth_on_exit': bool(values[POLICY_FIELDS[0]]),
        'idle_lock_time': int(values[POLICY_FIELDS[1]] or 0),
        'max_session_time': int(values[POLICY_FIELDS[2]] or 0),
    }


def client_policy_enabled(policy=None):
    return any((policy if policy is not None else client_login_policy()).values())


def client_login_lifetime(policy=None):
    """Only the page setting limits desktop login; token rotation is internal."""
    policy = policy if policy is not None else client_login_policy()
    return timedelta(minutes=policy['max_session_time']) if policy['max_session_time'] else None


def client_applications():
    Application = get_application_model()
    return Application.objects.filter(
        name=settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME, client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
    )


def is_client_application(application):
    return bool(application is not None
                and application.name == settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME
                and application.client_type == application.CLIENT_PUBLIC
                and application.authorization_grant_type == application.GRANT_AUTHORIZATION_CODE)


@contextmanager
def client_policy_lock():
    # Lock order everywhere: shared policy lock, DB transaction, session/token.
    # Reentrant because token views and settings updates call these services.
    with DistributedLock('client-login-policy', reentrant=True):
        yield


def _revoke_session(session, reason):
    if session.revoked_at is None:
        session.revoked_at = timezone.now()
        session.revoke_reason = reason
        session.save(update_fields=('revoked_at', 'revoke_reason'))
    get_refresh_token_model().revoke_family(session.token_family)


def revoke_session(session, reason='logout'):
    with client_policy_lock(), transaction.atomic():
        session = ClientLoginSession.objects.select_for_update().get(pk=session.pk)
        _revoke_session(session, reason)


def _session_is_valid(session, policy, now, *, mutate=False):
    session.client_login_policy = policy
    if session.revoked_at is not None:
        session.client_login_reason = (session.revoke_reason if session.revoke_reason in
                                       ClientLoginSession.RevokeReason.values else None)
        return False
    reason = None
    # DOT replay detection/admin revocation can bypass our revoke endpoint.
    # A refresh token may legitimately outlive its access token's expiry.
    live_refresh = get_refresh_token_model().objects.filter(
        application_id=session.application_id, token_family=session.token_family,
        revoked__isnull=True, access_token__isnull=False,
    ).exists()
    if not session.user.is_valid or not live_refresh:
        reason = 'security_revoke'
    else:
        deadline, expiry_reason = client_session_deadline(session)
        if deadline and now >= deadline:
            reason = expiry_reason
    session.client_login_reason = reason
    if reason:
        if mutate:
            _revoke_session(session, reason)
        return False
    return True


@contextmanager
def _session_operation(mutate):
    if mutate:
        with client_policy_lock(), transaction.atomic():
            yield
    else:
        # Generic API views use ATOMIC_REQUESTS. Holding a row lock there while
        # releasing the policy lock would invert lock order later in the view.
        yield


def validate_session(session_id, *, mutate=False):
    with _session_operation(mutate):
        queryset = ClientLoginSession.objects.select_related('user')
        if mutate:
            queryset = queryset.select_for_update()
        session = queryset.filter(pk=session_id).first()
        return bool(session and _session_is_valid(
            session, client_login_policy(), timezone.now(), mutate=mutate,
        ))


def _validate_family(application, user_id, family, *, mutate=False):
    policy = client_login_policy()
    queryset = ClientLoginSession.objects.select_related('user')
    if mutate:
        queryset = queryset.select_for_update()
    session = queryset.filter(
        application=application, token_family=family,
    ).first() if family else None
    if session is None or session.user_id != user_id:
        # Every desktop authorization needs its own server-owned login record.
        return None, False
    valid = _session_is_valid(session, policy, timezone.now(), mutate=mutate)
    return session, valid


def validate_access_token(token, *, mutate=False):
    if not is_client_application(getattr(token, 'application', None)):
        return None
    with _session_operation(mutate):
        refresh = get_refresh_token_model().objects.filter(access_token_id=token.pk).first()
        session, valid = _validate_family(
            token.application, token.user_id, refresh.token_family if refresh else None, mutate=mutate,
        )
        # A revoked family cannot become valid when all policies are disabled.
        valid = valid and get_access_token_model().objects.filter(pk=token.pk).exists()
    if not valid:
        raise ClientSessionExpired(session)
    return session


def validate_refresh_token_session(refresh):
    if not is_client_application(refresh.application):
        return True
    with client_policy_lock(), transaction.atomic():
        session, valid = _validate_family(refresh.application, refresh.user_id, refresh.token_family, mutate=True)
        refresh.client_login_session = session
        return valid


def schedule_client_policy_expiry():
    """Keep the original lifetime; schedule a separate exit after a policy change."""
    from django.db.models import Q
    deadline = timezone.now() + timedelta(minutes=10)
    ClientLoginSession.objects.filter(
        application__in=client_applications(), revoked_at__isnull=True,
    ).filter(Q(policy_expires_at__isnull=True) | Q(policy_expires_at__gt=deadline)).update(
        policy_expires_at=deadline,
    )


def revoke_client_authorizations(reason='policy_changed'):
    """Terminate old and managed authorizations, including unused OAuth codes."""
    with client_policy_lock(), transaction.atomic():
        applications = client_applications()
        now = timezone.now()
        ClientLoginSession.objects.filter(application__in=applications, revoked_at__isnull=True).update(
            revoked_at=now, revoke_reason=reason,
        )
        RefreshToken = get_refresh_token_model()
        refresh_tokens = RefreshToken.objects.filter(application__in=applications, revoked__isnull=True)
        for family in refresh_tokens.exclude(token_family=None).values_list('token_family', flat=True).distinct():
            # DOT handles duplicate live checksums when assigning revoked times.
            RefreshToken.revoke_family(family)
        for refresh in refresh_tokens.filter(token_family=None):
            refresh.revoke()
        get_access_token_model().objects.filter(application__in=applications).delete()
        get_grant_model().objects.filter(application__in=applications).delete()


def clear_client_login_sessions():
    """Keep terminated rows for 30 days and while OAuth credentials refer to them."""
    from django.db.models import Exists, OuterRef, Q

    with client_policy_lock(), transaction.atomic():
        # Authentication checks enforce these deadlines even if cleanup never runs.
        # Reclaim expired families here so page-only limits also release token rows.
        policy = client_login_policy()
        now = timezone.now()
        for session in ClientLoginSession.objects.select_related('user').filter(
            Q(expires_at__lte=now) | Q(policy_expires_at__lte=now), revoked_at__isnull=True,
        ):
            _session_is_valid(session, policy, now, mutate=True)
        refresh_tokens = get_refresh_token_model().objects.filter(
            application_id=OuterRef('application_id'), token_family=OuterRef('token_family'),
        )
        sessions = ClientLoginSession.objects.annotate(
            has_refresh=Exists(refresh_tokens),
            has_live_refresh=Exists(refresh_tokens.filter(revoked__isnull=True, access_token__isnull=False)),
        )
        # Tokens may have been revoked by the existing OAuth admin or cleanup path.
        sessions.filter(revoked_at__isnull=True, has_live_refresh=False).update(
            revoked_at=timezone.now(), revoke_reason='security_revoke',
        )
        # Also reclaim legacy credentials without a login record and credentials
        # whose session was invalidated by a migration or policy change.
        live_sessions = ClientLoginSession.objects.filter(
            application_id=OuterRef('application_id'), token_family=OuterRef('token_family'),
            revoked_at__isnull=True,
        )
        obsolete = get_refresh_token_model().objects.filter(application__in=client_applications()).annotate(
            has_live_session=Exists(live_sessions),
        ).filter(has_live_session=False)
        get_access_token_model().objects.filter(pk__in=obsolete.values('access_token_id')).delete()
        obsolete.delete()
        sessions.filter(revoked_at__lt=timezone.now() - timedelta(days=30), has_refresh=False).delete()
