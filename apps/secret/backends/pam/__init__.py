from django.db.models import Model

from ..base import BaseSecretClient


class PamSecretClient(BaseSecretClient):

    def __init__(self, instance: Model):
        super().__init__(instance)

    def update_or_create_secret(self):
        pass

    def delete_secret(self):
        pass

    def get_secret(self):
        pass


client = PamSecretClient
