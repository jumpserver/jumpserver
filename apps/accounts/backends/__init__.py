from django.conf import settings

from ..const import VaultType
from .local import LocalVault
from .vault import HCPVault

__all__ = ['vault_client']


vault_client_mapper = {
    VaultType.LOCAL: LocalVault,
    VaultType.HCP: HCPVault,
}


""" 为了安全, 重启后会重新初始化 vault_client """
vault_client = vault_client_mapper.get(settings.VAULT_TYPE, LocalVault)()
