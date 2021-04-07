

class ModelBackendMixin:
    """
    重写所有 Backend 的方法:
        1. def has_module_perms()
        2. def has_perm()
    """

    def has_module_perms(self, user_obj, app_label):
        return False

    def has_perm(self, user_obj, perm, obj=None):
        return False
