from django.conf import settings

from ..base import JMSBaseAuthBackend


class PasskeyAuthBackend(JMSBaseAuthBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_PASSKEY
