from django.db.models import Model
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from common.exceptions import JMSException
from .pam_api import PamAPi
from ..base import BaseSecretClient


class PamSecretClient(BaseSecretClient):

    def __init__(self, instance: Model):
        super().__init__(instance)
        self.client = PamAPi(
            settings.PAM_URL,
            username=settings.PAM_USERNAME,
            password=settings.PAM_PASSWORD
        )
        if not self.client.is_active:
            raise JMSException(
                code='init_pam_fail',
                detail=_('Initialization pam fail')
            )

    def update_or_create_secret(self, secret_data=None):
        pass

    def patch_secret(self, old_secret_data):
        pass

    def delete_secret(self):
        pass

    def get_secret(self):
        pass


client = PamSecretClient
