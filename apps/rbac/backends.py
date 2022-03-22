from django.core.exceptions import PermissionDenied

from authentication.backends.base import JMSBaseAuthBackend


class RBACBackend(JMSBaseAuthBackend):
    """ 只做权限校验 """
    @staticmethod
    def is_enabled():
        return True

    def authenticate(self, *args, **kwargs):
        return None

    def username_allow_authenticate(self, username):
        return False

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active or not perm:
            raise PermissionDenied()
        if perm == '*':
            return True
        perm_set = set(i.strip() for i in perm.split('|'))
        has_perm = bool(perm_set & set(user_obj.perms))
        if not has_perm:
            raise PermissionDenied()
        return has_perm

    # def has_module_perms(self, user_obj, app_label):
    #     return True
