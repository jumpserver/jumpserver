import importlib

from django.utils.translation import gettext_lazy as _

from assets.const import StorageType
from common.utils import get_logger
from common.exceptions import JMSException
from .base import BaseSecretClient

logger = get_logger(__name__)

__all__ = ['Secret']


class Secret:
    client: BaseSecretClient

    def __init__(self, instance, backend):
        if backend not in StorageType:
            raise JMSException(
                code='secret_storage_not_support',
                detail=_('Secret storage not support: {}').format(backend)
            )
        m = importlib.import_module(f'.{backend}', __package__)
        self.client = getattr(m, 'client')(instance)

    def update_or_create_secret(self):
        self.client.update_or_create_secret()

    def patch_secret(self, old_secret_data):
        self.client.patch_secret(old_secret_data)

    def delete_secret(self):
        self.client.delete_secret()

    def get_secret(self):
        return self.client.get_secret()

    def clear_secret(self):
        self.client.clear_secret()
