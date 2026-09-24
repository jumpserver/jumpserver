"""Revalidate an external certificate proof through MFA/approval, up to auth_login()."""
import time
from contextlib import contextmanager

from authentication.errors import SessionEmptyError
from users.models import User
from users.utils import LoginBlockUtil, LoginIpBlockUtil
from .binding import binding_version
from .configuration import REVISION, ensure_enabled, get_snapshot, locked_snapshot
from .exceptions import UKeyAuthError


def clear_pending_auth(request):
    """Discard an anonymous login attempt, preserving established-session gates."""
    if request.user.is_authenticated:
        return
    keys = (
        'auth_ukey', 'auth_ukey_state', 'auth_password', 'auth_password_expired_at',
        'user_id', 'auth_backend', 'auto_login',
        'auth_mfa', 'auth_mfa_time', 'auth_mfa_required', 'auth_mfa_type', 'auth_mfa_username',
        'auth_confirm_required', 'auth_notice_required', 'auth_ticket_id', 'auth_acl_id',
        'user_session_id', 'user_log_id', 'can_send_notifications',
    )
    for key in keys:
        request.session.pop(key, None)


def validate_pending_user(request, user, snapshot=None):
    from .backends import UKeyBackend
    state = request.session.get('auth_ukey_state') or {}
    snapshot = snapshot if snapshot is not None else get_snapshot()
    try:
        provider = ensure_enabled(snapshot, state.get('provider'))
        if (provider.binding_mode != 'certificate' or state.get('user_id') != str(user.pk)
                or state.get('revision') != snapshot[REVISION]
                or state.get('expires', 0) <= time.time()):
            raise UKeyAuthError('Pending UKey proof expired or changed')
        if not state.get('binding_version') or binding_version(user.pk, provider.id) != state['binding_version']:
            raise UKeyAuthError('Certificate binding changed')
        backend = UKeyBackend()
        if not backend.user_can_authenticate(user) or not backend.user_allow_authenticate(user):
            raise UKeyAuthError('User cannot authenticate with UKey')
    except UKeyAuthError:
        clear_pending_auth(request)
        raise SessionEmptyError() from None


@contextmanager
def final_login(request, user, ip):
    state = request.session.get('auth_ukey_state') or {}
    try:
        with locked_snapshot(state.get('revision')) as snapshot:
            user = User.objects.select_for_update().get(pk=user.pk)
            validate_pending_user(request, user, snapshot)
            if LoginIpBlockUtil(ip).is_block() or LoginBlockUtil(user.username, ip).is_block():
                raise UKeyAuthError('Login is blocked')
            yield user
    except (UKeyAuthError, User.DoesNotExist):
        clear_pending_auth(request)
        raise SessionEmptyError() from None
