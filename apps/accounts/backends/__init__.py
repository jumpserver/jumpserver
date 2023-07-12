from django.conf import settings

from ..const import VaultTypeChoices
from .local import LocalVault
from .vault import HCPVault

__all__ = ['vault_client']


vault_client_mapper = {
    VaultTypeChoices.local: LocalVault,
    VaultTypeChoices.hcp: HCPVault,
}


""" 为了安全, 页面修改后，重启服务后才会重新初始化 vault_client """
vault_client = vault_client_mapper.get(settings.VAULT_TYPE, LocalVault)()
