# -*- coding: utf-8 -*-
#
import os

from obs.client import ObsClient
from .base import ObjectStorage


class OBSStorage(ObjectStorage):
    def __init__(self, config):
        self.endpoint = config.get("ENDPOINT", None)
        self.bucket = config.get("BUCKET", None)
        self.access_key = config.get("ACCESS_KEY", None)
        self.secret_key = config.get("SECRET_KEY", None)
        if self.access_key and self.secret_key and self.endpoint:
            proxy_host = os.getenv("proxy_host")
            proxy_port = os.getenv("proxy_port")
            proxy_username = os.getenv("proxy_username")
            proxy_password = os.getenv("proxy_password")
            self.obsClient = ObsClient(access_key_id=self.access_key, secret_access_key=self.secret_key, server=self.endpoint, proxy_host=proxy_host, proxy_port=proxy_port, proxy_username=proxy_username, proxy_password=proxy_password)
        else:
            self.obsClient = None

    def upload(self, src, target):
        try:
            resp = self.obsClient.putFile(self.bucket, target, src)
            if resp.status < 300:
                return True, None
            else:
                return False, resp.reason
        except Exception as e:
            return False, e

    def exists(self, path):
        resp = self.obsClient.getObjectMetadata(self.bucket, path)
        if resp.status < 300:
            return True
        return False

    def delete(self, path):
        try:
            resp = self.obsClient.deleteObject(self.bucket, path)
            if resp.status < 300:
                return True, None
            else:
                return False, resp.reason
        except Exception as e:
            return False, e

    def download(self, src, target):
        try:
            os.makedirs(os.path.dirname(target), 0o755, exist_ok=True)
            resp = self.obsClient.getObject(self.bucket, src, target)
            if resp.status < 300:
                return True, None
            else:
                return False, resp.reason
        except Exception as e:
            return False, e

    def list_buckets(self):
        resp = self.obsClient.listBuckets()
        if resp.status < 300:
            return [b.name for b in resp.body.buckets]
        else:
            raise RuntimeError(resp.status, str(resp.reason))

    @property
    def type(self):
        return 'obs'
