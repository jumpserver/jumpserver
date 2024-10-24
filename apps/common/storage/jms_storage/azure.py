# -*- coding: utf-8 -*-
#

import os

from azure.storage.blob import BlobServiceClient

from .base import ObjectStorage


class AzureStorage(ObjectStorage):

    def __init__(self, config):
        self.account_name = config.get("ACCOUNT_NAME", None)
        self.account_key = config.get("ACCOUNT_KEY", None)
        self.container_name = config.get("CONTAINER_NAME", None)
        self.endpoint_suffix = config.get("ENDPOINT_SUFFIX", 'core.chinacloudapi.cn')

        if self.account_name and self.account_key:
            self.service_client = BlobServiceClient(
                account_url=f'https://{self.account_name}.blob.{self.endpoint_suffix}',
                credential={'account_name': self.account_name, 'account_key': self.account_key}
            )
            self.client = self.service_client.get_container_client(self.container_name)
        else:
            self.client = None

    def upload(self, src, target):
        try:
            self.client.upload_blob(target, src)
            return True, None
        except Exception as e:
            return False, e

    def download(self, src, target):
        try:
            blob_data = self.client.download_blob(blob=src)
            os.makedirs(os.path.dirname(target), 0o755, exist_ok=True)
            with open(target, 'wb') as writer:
                writer.write(blob_data.readall())
            return True, None
        except Exception as e:
            return False, e

    def delete(self, path):
        try:
            self.client.delete_blob(path)
            return True, False
        except Exception as e:
            return False, e

    def exists(self, path):
        resp = self.client.list_blobs(name_starts_with=path)
        return len(list(resp)) != 0

    def list_buckets(self):
        return list(self.service_client.list_containers())

    @property
    def type(self):
        return 'azure'
