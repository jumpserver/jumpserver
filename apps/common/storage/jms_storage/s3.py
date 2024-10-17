# -*- coding: utf-8 -*-
#
import boto3
import os

from .base import ObjectStorage


class S3Storage(ObjectStorage):
    def __init__(self, config):
        self.bucket = config.get("BUCKET", "jumpserver")
        self.region = config.get("REGION", None)
        self.access_key = config.get("ACCESS_KEY", None)
        self.secret_key = config.get("SECRET_KEY", None)
        self.endpoint = config.get("ENDPOINT", None)

        try:
            self.client = boto3.client(
                's3', region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                endpoint_url=self.endpoint
            )
        except ValueError:
            pass

    def upload(self, src, target):
        try:
            self.client.upload_file(Filename=src, Bucket=self.bucket, Key=target)
            return True, None
        except Exception as e:
            return False, e

    def exists(self, path):
        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
            return True
        except Exception as e:
            return False

    def download(self, src, target):
        try:
            os.makedirs(os.path.dirname(target), 0o755, exist_ok=True)
            self.client.download_file(self.bucket, src, target)
            return True, None
        except Exception as e:
            return False, e

    def delete(self, path):
        try:
            self.client.delete_object(Bucket=self.bucket, Key=path)
            return True, None
        except Exception as e:
            return False, e

    def generate_presigned_url(self, path, expire=3600):
        try:
            return self.client.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': self.bucket, 'Key': path},
                ExpiresIn=expire,
                HttpMethod='GET'), None
        except Exception as e:
            return False, e

    def list_buckets(self):
        response = self.client.list_buckets()
        buckets = response.get('Buckets', [])
        result = [b['Name'] for b in buckets if b.get('Name')]
        return result

    @property
    def type(self):
        return 's3'
