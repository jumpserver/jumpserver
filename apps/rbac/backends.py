from django.contrib.auth.backends import ModelBackend
from rbac.models import NamespaceRoleBinding, OrgRoleBinding, SystemRoleBinding


class RBACBackend(ModelBackend):

    @staticmethod
    def get_namespace_permissions(user_obj, namespace_id):
        perms = []
        bindings = NamespaceRoleBinding.objects.filter(user=user_obj, namespace=namespace_id).all()
        for i in bindings:
            perms += i.role.permissions.all().values_list('content_type__app_label', 'codename')
        return set(perms)

    @staticmethod
    def get_org_permissions(user_obj, org_id):
        perms = []
        bindings = OrgRoleBinding.objects.filter(user=user_obj, org=org_id).all()
        for i in bindings:
            perms += i.role.permissions.all().values_list('content_type__app_label', 'codename')
        return set(perms)

    @staticmethod
    def get_system_permissions(user_obj):
        perms = []
        bindings = SystemRoleBinding.objects.filter(user=user_obj).all()
        for i in bindings:
            perms += i.role.permissions.all().values_list('content_type__app_label', 'codename')
        return set(perms)

    def get_all_permissions(self, user_obj, namespace='', org=''):
        if not user_obj.is_active or user_obj.is_anonymous:
            return set()
        perms = self.get_system_permissions(user_obj)
        if org:
            perms.update(self.get_org_permissions(user_obj, org))
        if namespace:
            perms.update(self.get_namespace_permissions(user_obj, namespace))
        return ["%s.%s" % (ct, codename) for ct, codename in perms]

    def parse_perm(self, perm):
        cleaned_perm = {
            'perm': '',
        }
        if '|' not in perm:
            cleaned_perm['perm'] = perm
            return cleaned_perm
        perms = perm.split('|')
        perm = perms[-1]
        cleaned_perm['perm'] = perm
        for scope_val in perms[:-1]:
            scope, val = scope_val.split(':')
            if scope in ['ns', 'org']:
                cleaned_perm[scope] = val
        return cleaned_perm

    def has_perm(self, user_obj, perm, obj=None):
        """
        这里扩展一下 perm， 原来的perm 是 accounts.create_account，现在支持了多种scope的权限，所以我们定义一下格式
        ns:ns_id|org:org_id|module.action_model
        如: ns:82364313-97f2-44ad-b206-17c94fa2a82c|org:82364313-97f2-44ad-b206-17c94fa2a82c|accounts.create_account
        :param user_obj:
        :param perm:
        :param obj:
        :return:
        """
        scoped_perm = self.parse_perm(perm)
        namespace = scoped_perm.get('ns')
        org = scoped_perm.get('org')
        perm = scoped_perm.get('perm')
        permissions = self.get_all_permissions(user_obj, org=org, namespace=namespace)
        return user_obj.is_active and perm in permissions

    def has_module_perms(self, user_obj, app_label):
        return True
