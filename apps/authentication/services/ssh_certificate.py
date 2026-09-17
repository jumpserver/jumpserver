import time

import sshpubkeys
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from accounts.backends.openbao.service import OpenBaoAPIError, OpenBaoSSHCAClient
from accounts.const import SecretType
from accounts.exceptions import SSHCertificateSigningException
from assets.const import Protocol
from common.utils import get_logger, validate_ssh_public_key

logger = get_logger(__name__)

__all__ = ['sign_connection_token_ssh_certificate', 'get_ssh_ca_client']


def get_ssh_ca_client(config=None):
    config = config or settings
    addr = getattr(config, 'SSH_CA_OPENBAO_ADDR', '') or getattr(
        config, 'VAULT_OPENBAO_ADDR', ''
    ) or getattr(
        settings, 'VAULT_OPENBAO_ADDR', ''
    )
    return OpenBaoSSHCAClient(
        addr=addr,
        token=getattr(config, 'SSH_CA_OPENBAO_TOKEN', ''),
        mount_point=getattr(config, 'SSH_CA_OPENBAO_MOUNT_POINT', 'ssh-client-signer'),
        role=getattr(config, 'SSH_CA_OPENBAO_ROLE', 'jumpserver'),
        timeout=getattr(config, 'SSH_CA_OPENBAO_TIMEOUT', 10),
        verify_tls=getattr(config, 'SSH_CA_OPENBAO_VERIFY_TLS', True),
    )


def _validate_public_key(public_key):
    if public_key and len(public_key) > 16384:
        raise ValidationError({'public_key': _('SSH public key is too long')})
    if not public_key or not validate_ssh_public_key(public_key):
        raise ValidationError({'public_key': _('Not a valid ssh public key')})

    key_type = public_key.split(None, 1)[0]
    if '-cert-v01@openssh.com' in key_type:
        raise ValidationError({'public_key': _('An SSH certificate cannot be signed again')})

    key = sshpubkeys.SSHKey(public_key)
    key.parse()
    return key.hash_sha256()


def _get_ttl(token):
    configured_ttl = int(getattr(settings, 'SSH_CA_OPENBAO_TTL', 300) or 300)
    permission_ttl = int(token.expire_at - time.time())
    if permission_ttl <= 0:
        raise ValidationError(_('Asset permission has expired'))
    return max(1, min(configured_ttl, permission_ttl))


def sign_connection_token_ssh_certificate(token, public_key):
    if not getattr(settings, 'SSH_CA_ENABLED', False):
        raise SSHCertificateSigningException(_('SSH certificate signing is disabled'))

    account = token.account_object
    if not account or account.secret_type != SecretType.SSH_CERTIFICATE:
        raise ValidationError(_('The account does not use SSH certificate authentication'))
    if account.is_virtual():
        raise ValidationError(_('Virtual accounts cannot use SSH certificate authentication'))
    if not account.full_username:
        raise ValidationError(_('SSH certificate accounts require a username'))
    if token.protocol not in (Protocol.ssh, Protocol.sftp):
        raise ValidationError(_('SSH certificates only support SSH and SFTP protocols'))

    fingerprint = _validate_public_key(public_key)
    ttl = _get_ttl(token)
    extensions = (
        {'permit-pty': '', 'permit-port-forwarding': ''}
        if token.protocol == Protocol.ssh else None
    )
    source_address = getattr(settings, 'SSH_CA_OPENBAO_SOURCE_ADDRESS', '') or ''
    critical_options = (
        {'source-address': source_address.strip()}
        if source_address.strip() else None
    )
    key_id = f'jms-{token.id}'

    try:
        result = get_ssh_ca_client().sign(
            public_key=public_key.strip(),
            valid_principals=account.full_username,
            ttl=ttl,
            key_id=key_id,
            extensions=extensions,
            critical_options=critical_options,
        )
    except OpenBaoAPIError as e:
        logger.warning(
            'OpenBao SSH certificate signing failed: token=%s account=%s error=%s',
            token.id, account.id, e,
        )
        raise SSHCertificateSigningException() from e

    logger.info(
        'OpenBao SSH certificate issued: token=%s account=%s principal=%s '
        'serial=%s public_key=%s ttl=%s',
        token.id, account.id, account.full_username,
        result.get('serial_number', ''), fingerprint, result.get('lease_duration', ttl),
    )
    return {
        **result,
        'key_id': key_id,
        'principal': account.full_username,
        'public_key_fingerprint': fingerprint,
    }
