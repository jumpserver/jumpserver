from django.contrib.auth.backends import ModelBackend

from .models import RoleBinding


class RBACBackend(ModelBackend):
    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False

        has_perm = perm in user_obj.perms
        print("{} Perm {} in it: {}".format(user_obj, perm, has_perm))
        return has_perm
    #
    # def has_module_perms(self, user_obj, app_label):
    #     return True
