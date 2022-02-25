from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.backends import ModelBackend

from users.models import User
from common.utils import get_logger


logger = get_logger(__file__)


class JMSBaseAuthBackend:

    @staticmethod
    def is_enabled():
        return True

    def has_perm(self, user_obj, perm, obj=None):
        return False

    # can authenticate
    def username_can_authenticate(self, username):
        return self.allow_authenticate(username=username)

    def user_can_authenticate(self, user):
        if not self.allow_authenticate(user=user):
            return False
        is_valid = getattr(user, 'is_valid', None)
        return is_valid or is_valid is None

    @property
    def backend_path(self):
        return f'{self.__module__}.{self.__class__.__name__}'

    def allow_authenticate(self, user=None, username=None):
        if user:
            allowed_backends = user.get_allowed_auth_backends()
        else:
            allowed_backends = User.get_user_allowed_auth_backends(username)
        if allowed_backends is None:
            # 特殊值 None 表示没有限制
            return True
        allow = self.backend_path in allowed_backends
        if not allow:
            info = 'User {} skip authentication backend {}, because it not in {}'
            info = info.format(username, self.backend_path, ','.join(allowed_backends))
            logger.debug(info)
        return allow


class JMSModelBackend(JMSBaseAuthBackend, ModelBackend):
    pass
