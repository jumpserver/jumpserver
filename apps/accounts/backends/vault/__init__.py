import re
from abc import ABC
from datetime import datetime, timezone

from django.conf import settings
from django.db.models import Model
from django.utils.translation import ugettext_lazy as _

from common.db.utils import Encryptor
from common.exceptions import JMSException
from common.utils import get_logger
from common.utils.timezone import as_current_tz
from .base import BaseVault as PingVault
from .engine import VaultKVEngine
from ..base import BaseVaultClient

logger = get_logger(__name__)

__all__ = ['HCPVaultClient']

_MODEL_NAME_PATTERN = re.compile(r'(?<!^)(?=[A-Z])')


class HCPVaultClient(BaseVaultClient, ABC):

    def __init__(self, instance: Model):
        super().__init__(instance)
        self.client = VaultKVEngine(
            mount_point=settings.HCP_VAULT_MOUNT_POINT,
            url=settings.HCP_VAULT_HOST,
            token=settings.HCP_VAULT_TOKEN
        )
        if not self.client.is_active:
            raise JMSException(
                code='init_vault_fail',
                detail=_('Initialization vault fail')
            )

    @property
    def path(self):
        from accounts.models import Account, AccountTemplate
        instance = self.instance
        pk = instance.pk
        org_id = instance.org_id
        model_name = _MODEL_NAME_PATTERN.sub('_', instance._meta.object_name).lower()
        if isinstance(instance, Account):
            path = f'orgs/{org_id}/assets/{instance.asset_id}/{model_name}s/{pk}'
        elif isinstance(instance, AccountTemplate):
            path = f'orgs/{org_id}/{model_name}s/{pk}'
        else:
            path = 'error'
        return path

    @staticmethod
    def is_active(host=None, token=None):
        client = PingVault(url=host, token=token)
        return client.is_active

    def create(self):
        instance = self.instance
        secret = getattr(instance, '_secret', None)
        self.client.create(self.path, {'secret': secret})
        self.sync_basic_info()
        self.clear_local_secret()

    def update(self):
        instance = self.instance
        secret = getattr(instance, '_secret', None)
        self.client.patch(self.path, {'secret': secret})
        self.sync_basic_info()
        self.clear_local_secret()

    def delete(self):
        self.client.delete(self.path)

    def get(self):
        instance = self.instance
        if hasattr(instance, 'cache_secret'):
            return {'secret': instance.cache_secret}

        data = self.client.get(self.path).get('data', {})
        self.instance.cache_secret = data.get('secret')
        return data

    def get_history_data(self):
        metadata = self.client.get(self.path).get('metadata', {})
        version = metadata.get('version', 1)
        history_data = []
        if version == 1:
            return history_data
        for i in range(version - 1, 0, -1):
            data = self.client.get(self.path, version=i)
            secret = data.get('data').get('secret')
            history_date = data.get('metadata').get('created_time', '')
            if not history_date:
                history_date = ''
            else:
                history_date = datetime.strptime(history_date, '%Y-%m-%dT%H:%M:%S.%fZ')
                history_date = as_current_tz(history_date.replace(tzinfo=timezone.utc))
                history_date = history_date.strftime('%Y-%m-%d %H:%M:%S')
            history_data.append({
                'id': str(i),
                'version': str(i),
                'history_date': history_date,
                'secret': Encryptor(secret).decrypt(),
            })
        return history_data

    def sync_basic_info(self):
        data = self.get_instance_basic_info()
        self.client.update_metadata(self.path, data)
