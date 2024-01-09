from common.utils import get_logger
from ..base import BaseVault
from ...tasks.ris import get_asset_account_secret_from_ris

from jumpserver import settings as js_settings
from django.conf import settings

__all__ = ['Vault']

logger = get_logger(__name__)


class Vault(BaseVault):
    def is_active(self):
        return True, ''

    def _get(self, instance):
        ris_config_names = [k for k in js_settings.__dict__.keys() if k.startswith('VAULT_')]
        ris_configs = {name: getattr(settings, name, None) for name in ris_config_names}
        platform = str(instance.asset.platform).lower()
        if platform.__contains__('win'):
            os = 'windows'
        else:
            os = 'Linux'
        secret = get_asset_account_secret_from_ris(instance.username, os, instance.asset.address, ris_configs)
        return secret

    def _create(self, instance):
        """ Ignore """
        pass

    def _update(self, instance):
        """ Ignore """
        pass

    def _delete(self, instance):
        """ Ignore """
        pass

    def _save_metadata(self, instance, metadata):
        """ Ignore """
        pass

    def _clean_db_secret(self, instance):
        """ Ignore *重要* 不能删除本地 secret """
        pass
