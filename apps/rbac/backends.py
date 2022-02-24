from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied


class RBACBackend(ModelBackend):
    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            raise PermissionDenied()

        has_perm = perm in user_obj.perms
        print("has perm: ", perm)
        if not has_perm:
            raise PermissionDenied()
        return has_perm

    def authenticate(self, request, username=None, password=None, **kwargs):
        return None

    #
    # def has_module_perms(self, user_obj, app_label):
    #     return True
