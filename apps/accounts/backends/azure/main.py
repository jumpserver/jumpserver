from .service import AZUREVaultClient
from ..base.vault import BaseVault
from ..utils.mixins import GeneralVaultMixin
from ...const import VaultTypeChoices


class Vault(GeneralVaultMixin, BaseVault):
    type = VaultTypeChoices.azure

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = AZUREVaultClient(
            vault_url=kwargs.get('VAULT_AZURE_HOST'),
            tenant_id=kwargs.get('VAULT_AZURE_TENANT_ID'),
            client_id=kwargs.get('VAULT_AZURE_CLIENT_ID'),
            client_secret=kwargs.get('VAULT_AZURE_CLIENT_SECRET')
        )
