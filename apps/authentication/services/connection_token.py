from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException

from accounts.const import SecretType
from accounts.personal_credentials import (
    get_personal_credential_failure_reason, record_personal_credential_audit,
)
from common.utils import get_logger
from common.utils.http import is_false
from authentication.models import ConnectionToken
from .ssh_certificate import sign_connection_token_ssh_certificate

logger = get_logger(__name__)


def get_connection_token_secret(token, serializer_factory, *, expire_now=True, public_key=''):
    """Return credentials using the shared token validation and consumption rules."""
    requested_expire_now = expire_now
    try:
        if token.personal_credential_id:
            # Validate permissions and fetch the exact-version secret once.
            # account_object reuses it on this request-local token instance.
            token.is_valid(include_personal_secret=True)
        else:
            token.is_valid()
        account = token.account_object
    except Exception as error:
        if token.personal_credential_id:
            if isinstance(error, APIException):
                reason = get_personal_credential_failure_reason(error)
            else:
                reason = error.__class__.__name__
            record_personal_credential_audit(
                operation='use',
                result='failed',
                failure_reason=reason,
                user=token.user,
                asset=token.asset,
                credential_id=token.personal_credential_id,
                username=token.input_username,
                secret_type=token.input_secret_type,
                remote_addr=token.remote_addr,
                org_id=token.org_id,
            )
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
    if token.personal_credential_id:
        record_personal_credential_audit(
            operation='use',
            result=(
                'inspected'
                if is_false(requested_expire_now)
                else 'success'
            ),
            user=token.user,
            asset=token.asset,
            credential_id=token.personal_credential_id,
            username=token.input_username,
            secret_type=token.input_secret_type,
            remote_addr=token.remote_addr,
            org_id=token.org_id,
        )

    ConnectionToken.objects.filter(pk=token.pk).update(date_last_used=timezone.now())

    return serializer.data
