from contextlib import nullcontext

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from accounts.const import SecretType
from accounts.personal_credentials import (
    get_personal_credential_failure_reason, record_personal_credential_audit,
)
from common.utils import get_logger, get_request_ip_or_data
from common.utils.http import is_false
from authentication.models import ConnectionToken
from .ssh_certificate import sign_connection_token_ssh_certificate

logger = get_logger(__name__)


def record_connection_token_credential_audit(token, *, result, error=None, request=None):
    """Record personal credential use using token metadata, without reading its secret."""
    if not token.personal_credential_id:
        return

    failure_reason = ''
    if error is not None:
        failure_reason = (
            get_personal_credential_failure_reason(error)
            if isinstance(error, APIException)
            else error.__class__.__name__
        )
    record_personal_credential_audit(
        operation='use',
        result=result,
        failure_reason=failure_reason,
        user=token.user,
        asset=token.asset,
        credential_id=token.personal_credential_id,
        username=token.input_username,
        secret_type=token.input_secret_type,
        remote_addr=(
            get_request_ip_or_data(request)
            if request is not None else token.remote_addr
        ),
        org_id=token.org_id,
    )


def get_connection_token_secret(token, serializer_factory, *, expire_now=True, public_key=''):
    """Return credentials using the shared token validation and consumption rules."""
    from .client_login_session import client_policy_lock

    with client_policy_lock() if token.client_login_session_id else nullcontext():
        # Commit a discovered login timeout before the credential transaction.
        token.validate_client_login_session(mutate=True)
        return _get_connection_token_secret(
            token, serializer_factory, expire_now=expire_now, public_key=public_key,
        )


@transaction.atomic
def _get_connection_token_secret(token, serializer_factory, *, expire_now=True, public_key=''):
    # Serialize credential release with cancellation and competing consumers;
    # discard properties cached on the model before the lock was acquired.
    token = type(token).objects.select_for_update().get(pk=token.pk)
    requested_expire_now = expire_now
    try:
        # Only personal tokens load a version-bound credential during validation.
        # account_object reuses it on this request-local token instance.
        token.is_valid(include_personal_secret=True)
        account = token.account_object
    except Exception as error:
        record_connection_token_credential_audit(token, result='failed', error=error)
        raise
    if account and account.secret_type == SecretType.SSH_CERTIFICATE:
        certificate = sign_connection_token_ssh_certificate(token, public_key)
        # The certificate is public material, but returning it through the
        # existing account credential field keeps the component contract
        # compact. Koko pairs it with the private key generated in memory.
        account.secret = certificate['signed_key']
        token.ssh_certificate = {
            key: value for key, value in certificate.items()
            if key != 'signed_key'
        }

    serializer = serializer_factory(instance=token)

    expire_now = requested_expire_now
    asset_type = token.asset.type
    # 设置默认值
    if asset_type in ['k8s', 'kubernetes']:
        expire_now = False

    if token.is_reusable and settings.CONNECTION_TOKEN_REUSABLE:
        logger.debug('Token is reusable, not expire now')
    elif is_false(expire_now):
        logger.debug('API specified, do not expire now')
    else:
        token.expire()

    # expire_now=false still returns the secret. Audit every disclosure,
    # while distinguishing Koko's inspection phase from final consumption.
    record_connection_token_credential_audit(
        token,
        result='inspected' if is_false(requested_expire_now) else 'success',
    )

    ConnectionToken.objects.filter(pk=token.pk).update(date_last_used=timezone.now())

    return serializer.data
