from .service import AmazonSecretsManagerClient
from ..base.vault import BaseVault
from ..utils.mixins import GeneralVaultMixin
from ...const import VaultTypeChoices


class Vault(GeneralVaultMixin, BaseVault):
    type = VaultTypeChoices.aws

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = AmazonSecretsManagerClient(
            region_name=kwargs.get('VAULT_AWS_REGION_NAME'),
            access_key_id=kwargs.get('VAULT_AWS_ACCESS_KEY_ID'),
            secret_key=kwargs.get('VAULT_AWS_ACCESS_SECRET_KEY'),
        )
