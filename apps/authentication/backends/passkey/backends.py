from django.conf import settings

from ..base import JMSModelBackend


class PasskeyAuthBackend(JMSModelBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_PASSKEY

    def user_can_authenticate(self, user):
        return user.source == 'local'
