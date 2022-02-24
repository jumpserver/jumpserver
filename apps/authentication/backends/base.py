from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class JMSBaseAuthBackend(BaseBackend):
    def authenticate(self, *args, **kwargs):
        return

    @classmethod
    def is_enabled(cls):
        return True

    def username_can_authenticate(self, username, *args):
        # self.name
        return True

    def user_can_authenticate(self, user):
        return True


class JMSModelBackend(JMSBaseAuthBackend, ModelBackend):
    def has_perm(self, user_obj, perm, obj=None):
        return False

    def user_can_authenticate(self, user):
        return True

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if user.is_valid else None
