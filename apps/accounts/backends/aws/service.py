import boto3

from common.utils import get_logger, random_string


logger = get_logger(__name__)

__all__ = ['AmazonSecretsManagerClient']


class AmazonSecretsManagerClient(object):
    def __init__(self, region_name, access_key_id, secret_key):
        self.client = boto3.client(
            'secretsmanager', region_name=region_name,
            aws_access_key_id=access_key_id, aws_secret_access_key=secret_key,
        )
        self.empty_secret = '#{empty}#'

    def is_active(self):
        try:
            secret_id = f'jumpserver/test-{random_string(12)}'
            self.create(secret_id, 'secret')
            self.get(secret_id)
            self.update(secret_id, 'secret')
            self.delete(secret_id)
        except Exception as e:
            return False, f'Vault is not reachable: {e}'
        else:
            return True, ''

    def get(self, name, version=''):
        params = {'SecretId': name}
        if version:
            params['VersionStage'] = version

        try:
            secret = self.client.get_secret_value(**params)['SecretString']
            return secret if secret != self.empty_secret else ''
        except Exception as e:
            logger.error(f"Error retrieving secret: {e}")
            return ''

    def create(self, name, secret):
        self.client.create_secret(Name=name, SecretString=secret or self.empty_secret)

    def update(self, name, secret):
        self.client.update_secret(SecretId=name, SecretString=secret or self.empty_secret)

    def delete(self, name):
        self.client.delete_secret(SecretId=name)

    def update_metadata(self, name, metadata: dict):
        tags = [{'Key': k, 'Value': v} for k, v in metadata.items()]
        try:
            self.client.tag_resource(SecretId=name, Tags=tags)
        except Exception as e:
            logger.error(f'update_metadata: {name} {str(e)}')
