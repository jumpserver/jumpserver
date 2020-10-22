
from django.contrib.auth.backends import ModelBackend as _ModelBackend
from namespaces.models import Namespace
from rbac.models import RoleNamespaceBinding, RoleOrgBinding


class RBACBackend(_ModelBackend):

    @staticmethod
    def get_namespace_permissions(user_obj, obj):
        perms = []
        bindings = RoleNamespaceBinding.objects.filter(user=user_obj, namespace=obj).all()
        for i in bindings:
            perms += i.role.permissions.all().values_list('content_type__app_label', 'codename')
        return set(perms)

    @staticmethod
    def get_org_permissions(user_obj, obj):
        perms = []
        org_id = obj.org_id
        if not org_id:
            return set(perms)
        bindings = RoleOrgBinding.objects.filter(user=user_obj, org=org_id).all()
        for i in bindings:
            perms += i.role.permissions.all().values_list('content_type__app_label', 'codename')
        return set(perms)

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous:
            return set()
        perms = {
            *self.get_namespace_permissions(user_obj, obj),
            *self.get_org_permissions(user_obj, obj)
        }
        return ["%s.%s" % (ct, codename) for ct, codename in perms]

    def has_perm(self, user_obj, perm, obj=None):
        if not obj or not isinstance(obj, Namespace):
            return True
        if user_obj.is_build_in:
            return True
        return user_obj.is_active and perm in self.get_all_permissions(user_obj, obj)

    def has_module_perms(self, user_obj, app_label):
        return True
