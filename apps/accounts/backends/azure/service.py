# -*- coding: utf-8 -*-
#
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient

from common.utils import get_logger

logger = get_logger(__name__)

__all__ = ['AZUREVaultClient']


class AZUREVaultClient(object):

    def __init__(self, vault_url, tenant_id, client_id, client_secret):
        authentication_endpoint = 'https://login.microsoftonline.com/' \
            if ('azure.net' in vault_url) else 'https://login.chinacloudapi.cn/'

        credentials = ClientSecretCredential(
            client_id=client_id, client_secret=client_secret, tenant_id=tenant_id, authority=authentication_endpoint
        )
        self.client = SecretClient(vault_url=vault_url, credential=credentials)

    def is_active(self):
        try:
            self.client.set_secret('jumpserver', '666')
        except (ResourceNotFoundError, ClientAuthenticationError) as e:
            logger.error(str(e))
            return False, f'Vault is not reachable: {e}'
        else:
            return True, ''

    def get(self, name, version=None):
        try:
            secret = self.client.get_secret(name, version)
            return secret.value
        except (ResourceNotFoundError, ClientAuthenticationError) as e:
            logger.error(f'get: {name} {str(e)}')
            return ''

    def create(self, name, secret):
        if not secret:
            secret = ''
        self.client.set_secret(name, secret)

    def update(self, name, secret):
        if not secret:
            secret = ''
        self.client.set_secret(name, secret)

    def delete(self, name):
        self.client.begin_delete_secret(name)

    def update_metadata(self, name, metadata: dict):
        try:
            self.client.update_secret_properties(name, tags=metadata)
        except (ResourceNotFoundError, ClientAuthenticationError) as e:
            logger.error(f'update_metadata: {name} {str(e)}')
