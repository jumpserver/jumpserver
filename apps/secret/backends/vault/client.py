from typing import List

import hvac
from requests.exceptions import ConnectionError

from django.conf import settings
from common.utils import get_logger

logger = get_logger(__name__)


class VaultClient:

    def __init__(self, url):
        self.client = hvac.Client(url=url)
        self.client.is_active = False
        vault_client.check_base_token_authentication(settings.VAULT_TOKEN)

    @property
    def is_active(self):
        return self.client.is_active

    def check_vault_initialized(self):
        return self.client.sys.is_initialized()

    def check_vault_sealed(self):
        return self.client.sys.is_sealed()

    def check_base_token_authentication(self, token):
        self.client.token = token
        try:
            if self.check_vault_initialized() and not self.check_vault_sealed():
                self.client.is_active = self.client.is_authenticated()
        except ConnectionError as e:
            logger.error(str(e))

    def unseal(self, keys: List):
        for key in keys:
            self.client.sys.unseal(key)


vault_client = VaultClient(settings.VAULT_URL)
