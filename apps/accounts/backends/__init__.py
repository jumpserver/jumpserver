from django.conf import settings

from .local import LocalVaultClient
from .vault import HCPVaultClient
from ..const import VaultType

VAULT_CLIENT_MAPPER = {
    VaultType.LOCAL: LocalVaultClient,
    VaultType.HCP: HCPVaultClient,
}


def get_vault_client(instance=None):
    client_cls = VAULT_CLIENT_MAPPER.get(
        settings.VAULT_TYPE, LocalVaultClient
    )
    return client_cls(instance)
