from contextlib import contextmanager
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from oauth2_provider.models import get_access_token_model, get_application_model, get_grant_model, get_refresh_token_model
from rest_framework.exceptions import AuthenticationFailed

POLICY_FIELDS = {
    'SECURITY_CLIENT_REAUTH_ON_EXIT': 'reauth_on_exit',
    'SECURITY_CLIENT_MAX_SESSION_TIME': 'max_session_time',
}


class ClientSessionExpired(AuthenticationFailed):
    default_detail = _('Client login session expired. Please authenticate again.')
    default_code = 'client_session_expired'


def client_login_policy():
    from settings.models import Setting

    # Read authoritative settings: worker broadcasts may not have arrived yet.
    values = {name: getattr(settings, name) for name in POLICY_FIELDS}
    values.update({item.name: item.cleaned_value for item in Setting.objects.filter(name__in=POLICY_FIELDS)})
    return {key: values[name] for name, key in POLICY_FIELDS.items()}


def client_applications():
    Application = get_application_model()
    return Application.objects.filter(
        name=settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME, client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
    )


def is_client_application(application):
    return bool(application and application.name == settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME
                and application.client_type == application.CLIENT_PUBLIC
                and application.authorization_grant_type == application.GRANT_AUTHORIZATION_CODE)


@contextmanager
def client_policy_transaction():
    # Serialize credential issuance, revocation and policy changes on
    # the existing application row. Ordinary API checks only read session state.
    with transaction.atomic():
        list(client_applications().order_by('pk').select_for_update())
        yield


def client_refresh_is_valid(refresh, policy):
    if refresh.revoked is not None or not refresh.access_token_id or not refresh.user.is_valid:
        return False
    lifetime = policy['max_session_time']
    return not lifetime or timezone.now() < refresh.created + timedelta(minutes=lifetime)


def client_session_data(refresh, policy):
    lifetime = policy['max_session_time']
    expires_at = refresh.created + timedelta(minutes=lifetime) if lifetime else None
    return {
        'client_login_policy': policy,
        'client_login_session': {
            'authenticated_at': refresh.created.isoformat(),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'server_time': timezone.now().isoformat(),
        },
    }


def validate_client_access_token(token, *, lock=False):
    if not is_client_application(token.application):
        return
    queryset = get_refresh_token_model().objects.select_related('user')
    if lock:
        queryset = queryset.select_for_update()
    refresh = queryset.filter(access_token_id=token.pk).first()
    # AccessToken's row is reused during refresh. A previously authenticated
    # snapshot must not validate the session or authorize new tickets after rotation.
    if (not refresh or not get_access_token_model().objects.filter(pk=token.pk, token=token.token).exists()
            or not client_refresh_is_valid(refresh, client_login_policy())):
        raise ClientSessionExpired()
    return refresh


def connection_session_id(access_token):
    """Bind a preissued connection ticket to the login that authorized it."""
    if not is_client_application(getattr(access_token, 'application', None)):
        return None
    with client_policy_transaction():
        return validate_client_access_token(access_token, lock=True).pk


def validate_connection_session(session_id):
    if not isinstance(session_id, int) or isinstance(session_id, bool) or session_id <= 0:
        raise ClientSessionExpired()
    refresh = get_refresh_token_model().objects.select_related('user').filter(
        pk=session_id, application__in=client_applications(),
    ).first()
    if not refresh or not client_refresh_is_valid(refresh, client_login_policy()):
        raise ClientSessionExpired()


def revoke_client_authorizations():
    """Policy edits require a fresh login, including previously unlimited logins."""
    applications = client_applications()
    # Match DOT's administrative revoke lock order: refresh token, then access.
    list(get_refresh_token_model().objects.filter(application__in=applications).order_by('pk').select_for_update())
    get_access_token_model().objects.filter(application__in=applications).delete()
    get_refresh_token_model().objects.filter(application__in=applications).delete()
    get_grant_model().objects.filter(application__in=applications).delete()
