from django.conf import settings

from ..const import VaultTypeChoices
from .local import LocalVault
from .vault import HCPVault

__all__ = ['vault_client', 'get_vault_client']


vault_client_mapper = {
    VaultTypeChoices.local: LocalVault,
    VaultTypeChoices.hcp: HCPVault,
}


def get_vault_client(**kwargs):
    tp = kwargs.get('VAULT_TYPE')
    vault_class = vault_client_mapper.get(tp, LocalVault)
    return vault_class(**kwargs)


""" 为了安全, 页面修改配置, 重启服务后才会重新初始化 vault_client """
vault_configs = {k: v for k, v in settings.__dict__.items() if k.startswith('VAULT_')}
vault_client = get_vault_client(**vault_configs)
