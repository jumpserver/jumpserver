from django.conf import settings
from django.utils.module_loading import import_string
from common.utils import get_logger
from django.contrib.auth import get_user_model
from authentication.signals import user_auth_failed, user_auth_success


from .base import JMSModelBackend

logger = get_logger(__file__)


class CustomAuthBackend(JMSModelBackend):
    custom_auth_method_path = 'data.auth.main.authenticate'

    def load_authenticate_method(self):
        return import_string(self.custom_auth_method_path)

    def is_enabled(self):
        try:
            self.load_authenticate_method()
        except Exception as e:
            logger.warning('Not enabled custom auth backend: {}'.format(e))
            return False
        else:
            logger.info('Enabled custom auth backend')
            return True

    @staticmethod
    def get_or_create_user_from_userinfo(userinfo: dict):
        username = userinfo['username']
        attrs = ['name', 'username', 'email', 'is_active']
        defaults = {attr: userinfo[attr] for attr in attrs}
        user, created = get_user_model().objects.get_or_create(
            username=username, defaults=defaults
        )
        return user, created

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            authenticate = self.load_authenticate_method()
            userinfo: dict = authenticate(username=username, password=password, **kwargs)
            user, created = self.get_or_create_user_from_userinfo(userinfo)
        except Exception as e:
            logger.error('Custom authenticate error: {}'.format(e))
            return None

        if self.user_can_authenticate(user):
            logger.info(f'Custom authenticate success: {user.username}')
            user_auth_success.send(
                sender=self.__class__, request=request, user=user,
                backend=settings.AUTH_BACKEND_CUSTOM
            )
            return user
        else:
            logger.info(f'Custom authenticate failed: {user.username}')
            user_auth_failed.send(
                sender=self.__class__, request=request, username=user.username,
                reason=_('User invalid, disabled or expired'),
                backend=settings.AUTH_BACKEND_CUSTOM
            )
            return None
