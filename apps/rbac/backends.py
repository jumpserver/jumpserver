from django.contrib.auth.backends import ModelBackend


class RBACBackends(ModelBackend):

    def has_perm(self, user_obj, perm, obj=None):
        return False

    def has_module_perms(self, user_obj, app_label):
        return False
