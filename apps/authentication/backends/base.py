from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

from users.models import User
from common.utils import get_logger


UserModel = get_user_model()
logger = get_logger(__file__)


class JMSBaseAuthBackend:

    @staticmethod
    def is_enabled():
        return True

    def has_perm(self, user_obj, perm, obj=None):
        return False

    def user_can_authenticate(self, user):
        """
        Reject users with is_valid=False. Custom user models that don't have
        that attribute are allowed.
        """
        # 三方用户认证完成后，在后续的 get_user 获取逻辑中，也应该需要检查用户是否有效
        is_valid = getattr(user, 'is_valid', None)
        return is_valid or is_valid is None

    # allow user to authenticate
    def username_allow_authenticate(self, username):
        return self.allow_authenticate(username=username)

    def user_allow_authenticate(self, user):
        return self.allow_authenticate(user=user)

    def allow_authenticate(self, user=None, username=None):
        if user:
            allowed_backend_paths = user.get_allowed_auth_backend_paths()
        else:
            allowed_backend_paths = User.get_user_allowed_auth_backend_paths(username)
        if allowed_backend_paths is None:
            # 特殊值 None 表示没有限制
            return True
        backend_name = self.__class__.__name__
        allowed_backend_names = [path.split('.drf.py')[-1] for path in allowed_backend_paths]
        allow = backend_name in allowed_backend_names
        if not allow:
            info = 'User {} skip authentication backend {}, because it not in {}'
            info = info.format(username, backend_name, ','.join(allowed_backend_names))
            logger.info(info)
        return allow

    def get_user(self, user_id):
        """ 三方用户认证成功后 request.user 赋值时会调用 backend 的当前方法获取用户 """
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None


class JMSModelBackend(JMSBaseAuthBackend, ModelBackend):
    pass
