from urllib.parse import quote, urlsplit

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from accounts.backends import VaultClient
from accounts.const import VaultTypeChoices
from common.utils import get_logger
from common.utils.lock import DistributedLock
from ops.celery.decorator import after_app_ready_start, register_as_period_task
from settings.models import Setting
from settings.signal_handlers import setting_pub_sub

__all__ = ['rotate_openbao_token']

logger = get_logger(__name__)

APPROLE_SETTING = 'VAULT_OPENBAO_ROTATION_APPROLE'
TOKEN_SETTING = 'VAULT_OPENBAO_TOKEN'
ROTATE_BEFORE = 7 * 24 * 60 * 60


def get_rotation_client():
    vault = VaultClient()
    if not vault.enabled or vault.type != VaultTypeChoices.openbao:
        raise ValueError('JumpServer must use the OpenBao vault backend.')
    if urlsplit(vault.client.addr).scheme != 'https' or not vault.client.verify_tls:
        raise ValueError('OpenBao token rotation requires HTTPS with TLS verification.')
    return vault


def configure_approle(auth_mount, role_id, secret_id):
    mount_parts = auth_mount.strip('/').split('/')
    if any(not part or part in ('.', '..') for part in mount_parts):
        raise ValueError('Enter a valid OpenBao AppRole auth mount.')
    if not all(isinstance(value, str) and value.strip() for value in (role_id, secret_id)):
        raise ValueError('Enter both the AppRole role ID and secret ID.')

    vault = get_rotation_client()
    Setting.update_or_create(
        name=APPROLE_SETTING,
        value={
            'address': vault.client.addr,
            'mount': '/'.join(mount_parts),
            'role_id': role_id,
            'secret_id': secret_id,
        },
        encrypted=True,
        category='openbao',
    )


def _lookup_token(client):
    if not client.token:
        return {}
    response = client._send('GET', '/v1/auth/token/lookup-self')
    if response.status_code == 403:
        return {}
    if response.status_code != 200:
        raise RuntimeError(f'OpenBao token lookup returned HTTP {response.status_code}.')
    return response.json()['data']


def _rotate_token(approle, force):
    vault = get_rotation_client()
    client = vault.client
    if client.addr != approle['address']:
        raise RuntimeError('OpenBao address changed. Reconfigure the rotation AppRole.')

    saved = Setting.objects.filter(name=TOKEN_SETTING).first()
    saved_token = saved.cleaned_value if saved else None
    previous_token = saved_token if saved else client.token
    client.token = previous_token or ''
    login_path = f"auth/{approle['mount']}/login"
    if not force:
        current = _lookup_token(client)
        if current.get('path') == login_path and current.get('ttl', 0) > ROTATE_BEFORE:
            # Repeat the notification in case a process missed an earlier one.
            setting_pub_sub.publish(TOKEN_SETTING)
            logger.info('OpenBao token retained. Remaining TTL: %s seconds.', current['ttl'])
            return 'retained'

    client.token = ''
    response = client._send('POST', '/v1/' + quote(login_path, safe='/'), json={
        'role_id': approle['role_id'],
        'secret_id': approle['secret_id'],
    })
    if response.status_code != 200:
        raise RuntimeError(f'OpenBao AppRole login returned HTTP {response.status_code}.')

    new_token = response.json()['auth']['client_token']
    if not new_token or new_token == previous_token:
        raise RuntimeError('OpenBao did not issue a distinct token.')
    client.token = new_token
    issued = _lookup_token(client)
    if issued.get('path') != login_path or issued.get('ttl', 0) <= ROTATE_BEFORE:
        raise RuntimeError('The new OpenBao token must support self lookup and last over seven days.')
    if not vault.is_active()[0]:
        raise RuntimeError('The new token failed the JumpServer OpenBao operation check.')

    with transaction.atomic():
        current = Setting.objects.select_for_update().filter(name=TOKEN_SETTING).first()
        if (current.cleaned_value if current else None) != saved_token:
            raise RuntimeError('The configured OpenBao token changed during rotation.')
        Setting.update_or_create(
            name=TOKEN_SETTING, value=new_token, encrypted=True, category='openbao',
        )
    Setting.refresh_item(TOKEN_SETTING)
    logger.info('OpenBao token rotated. New TTL: %s seconds.', issued['ttl'])
    return 'rotated'


@shared_task(verbose_name=_('Check and rotate the OpenBao vault token'))
@after_app_ready_start
@register_as_period_task(crontab='0 */8 * * *')
def rotate_openbao_token(force=False):
    if not settings.VAULT_ENABLED or settings.VAULT_BACKEND != VaultTypeChoices.openbao:
        return 'disabled'
    config = Setting.objects.filter(name=APPROLE_SETTING, enabled=True).first()
    if config is None:
        return 'disabled'
    if not config.encrypted:
        raise RuntimeError('OpenBao rotation requires encrypted AppRole credentials.')

    lock = DistributedLock('accounts:openbao-token-rotation')
    if not lock.acquire(blocking=False):
        return 'already_running'
    try:
        return _rotate_token(config.cleaned_value, force)
    finally:
        lock.release()
