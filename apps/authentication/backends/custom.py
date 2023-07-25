from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from authentication.signals import user_auth_failed, user_auth_success
from common.utils import get_logger
from .base import JMSModelBackend

logger = get_logger(__file__)

custom_authenticate_method = None

if settings.AUTH_CUSTOM:
    """ 保证自定义认证方法在服务运行时不能被更改，只在第一次调用时加载一次 """
    try:
        custom_auth_method_path = 'data.auth.main.authenticate'
        custom_authenticate_method = import_string(custom_auth_method_path)
    except Exception as e:
        logger.warning('Import custom auth method failed: {}, Maybe not enabled'.format(e))


class CustomAuthBackend(JMSModelBackend):

    def is_enabled(self):
        return settings.AUTH_CUSTOM and callable(custom_authenticate_method)

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
            userinfo: dict = custom_authenticate_method(
                username=username, password=password, **kwargs
            )
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
