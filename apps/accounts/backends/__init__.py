from importlib import import_module

from django.utils.functional import LazyObject

from common.utils import get_logger
from ..const import VaultTypeChoices

__all__ = ['vault_client', 'get_vault_client']


logger = get_logger(__file__)


def get_vault_client(raise_exception=False, **kwargs):
    try:
        ris_enabled = kwargs.get('RIS_ENABLED')
        if ris_enabled:
            tp = VaultTypeChoices.ris
            module_path = f'apps.accounts.backends.{tp}.main'
            client = import_module(module_path).Ris(**kwargs)
            return client

        vault_enabled = kwargs.get('VAULT_ENABLED')
        tp = VaultTypeChoices.hcp if vault_enabled else VaultTypeChoices.local
        module_path = f'apps.accounts.backends.{tp}.main'
        client = import_module(module_path).Vault(**kwargs)

    except Exception as e:
        logger.error(f'Init vault client failed: {e}')
        if raise_exception:
            raise
        tp = VaultTypeChoices.local
        module_path = f'apps.accounts.backends.{tp}.main'
        client = import_module(module_path).Vault(**kwargs)
    return client


class VaultClient(LazyObject):

    def _setup(self):
        from jumpserver import settings as js_settings
        from django.conf import settings
        vault_config_names = [k for k in js_settings.__dict__.keys() if k.startswith('VAULT_') or k.startswith('RIS_')]
        vault_configs = {name: getattr(settings, name, None) for name in vault_config_names}
        self._wrapped = get_vault_client(**vault_configs)


""" 为了安全, 页面修改配置, 重启服务后才会重新初始化 vault_client """
vault_client = VaultClient()
