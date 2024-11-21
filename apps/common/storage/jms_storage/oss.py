# -*- coding: utf-8 -*-
#
import os
import time

import oss2

from .base import ObjectStorage


class OSSStorage(ObjectStorage):
    def __init__(self, config):
        self.endpoint = config.get("ENDPOINT", None)
        self.bucket = config.get("BUCKET", None)
        self.access_key = config.get("ACCESS_KEY", None)
        self.secret_key = config.get("SECRET_KEY", None)
        if self.access_key and self.secret_key:
            self.auth = oss2.Auth(self.access_key, self.secret_key)
        else:
            self.auth = None
        if self.auth and self.endpoint and self.bucket:
            self.client = oss2.Bucket(self.auth, self.endpoint, self.bucket)
        else:
            self.client = None

    def upload(self, src, target):
        try:
            self.client.put_object_from_file(target, src)
            return True, None
        except Exception as e:
            return False, e

    def exists(self, path):
        try:
            return self.client.object_exists(path)
        except Exception as e:
            return False

    def delete(self, path):
        try:
            self.client.delete_object(path)
            return True, None
        except Exception as e:
            return False, e

    def restore(self, path):
        meta = self.client.head_object(path)
        if meta.resp.headers['x-oss-storage-class'] == oss2.BUCKET_STORAGE_CLASS_ARCHIVE:
            self.client.restore_object(path)
            while True:
                meta = self.client.head_object(path)
                if meta.resp.headers['x-oss-restore'] == 'ongoing-request="true"':
                    time.sleep(5)
                else:
                    break

    def download(self, src, target):
        try:
            os.makedirs(os.path.dirname(target), 0o755, exist_ok=True)
            self.restore(src)
            self.client.get_object_to_file(src, target)
            return True, None
        except Exception as e:
            return False, e

    def list_buckets(self):
        service = oss2.Service(self.auth,self.endpoint)
        return ([b.name for b in oss2.BucketIterator(service)])

    @property
    def type(self):
        return 'oss'
