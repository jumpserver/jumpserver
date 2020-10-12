
from django.contrib.auth.backends import ModelBackend as _ModelBackend
from rbac.models import RoleBinding


class RBACBackend(_ModelBackend):

    def get_all_permissions(self, user_obj, obj=None):
        perms = []
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()
        role_binding = RoleBinding.objects.filter(user=user_obj).all()
        for i in role_binding:
            perms += i.role.permissions.all().values_list('content_type__app_label', 'codename')
        return ["%s.%s" % (ct, codename) for ct, codename in perms]

    def has_perm(self, user_obj, perm, obj=None):
        if user_obj.is_build_in:
            return True
        return user_obj.is_active and perm in self.get_all_permissions(user_obj)

    def has_module_perms(self, user_obj, app_label):
        return True
