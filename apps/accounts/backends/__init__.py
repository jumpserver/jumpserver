from django.conf import settings

from .local import LocalVault
from .vault import HCPVault
from ..const import VaultType

VAULT_CLIENT_MAPPER = {
    VaultType.LOCAL: LocalVault,
    VaultType.HCP: HCPVault,
}


def get_vault_client(instance=None):
    client_cls = VAULT_CLIENT_MAPPER.get(
        settings.VAULT_TYPE, LocalVault
    )
    return client_cls()
