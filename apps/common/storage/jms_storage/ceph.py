# -*- coding: utf-8 -*-
#

import os
import boto
import boto.s3.connection

from .base import ObjectStorage


class CEPHStorage(ObjectStorage):

    def __init__(self, config):
        self.bucket = config.get("BUCKET", None)
        self.region = config.get("REGION", None)
        self.access_key = config.get("ACCESS_KEY", None)
        self.secret_key = config.get("SECRET_KEY", None)
        self.hostname = config.get("HOSTNAME", None)
        self.port = config.get("PORT", 7480)

        if self.hostname and self.access_key and self.secret_key:
            self.conn = boto.connect_s3(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                host=self.hostname,
                port=self.port,
                is_secure=False,
                calling_format=boto.s3.connection.OrdinaryCallingFormat(),
            )

        try:
            self.client = self.conn.get_bucket(bucket_name=self.bucket)
        except Exception:
            self.client = None

    def upload(self, src, target):
        try:
            key = self.client.new_key(target)
            key.set_contents_from_filename(src)
            return True, None
        except Exception as e:
            return False, e

    def download(self, src, target):
        try:
            os.makedirs(os.path.dirname(target), 0o755, exist_ok=True)
            key = self.client.get_key(src)
            key.get_contents_to_filename(target)
            return True, None
        except Exception as e:
            return False, e

    def delete(self, path):
        try:
            self.client.delete_key(path)
            return True, None
        except Exception as e:
            return False, e

    def exists(self, path):
        try:
            return self.client.get_key(path)
        except Exception:
            return False

    @property
    def type(self):
        return 'ceph'
