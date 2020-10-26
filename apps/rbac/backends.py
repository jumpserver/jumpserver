from django.contrib.auth.backends import ModelBackend
from rbac.models import NamespaceRoleBinding, OrgRoleBinding, SystemRoleBinding


class RBACBackend(ModelBackend):

    @staticmethod
    def format_perms(perms):
        return ["%s.%s" % (ct, codename) for ct, codename in perms]

    def get_namespace_permissions(self, user_obj, namespace_id, org_id):
        perms = []
        if org_id == 'DEFAULT':
            bindings = NamespaceRoleBinding.objects.filter(user=user_obj, namespace=namespace_id).all()
        else:
            bindings = NamespaceRoleBinding.objects.\
                filter(user=user_obj, namespace=namespace_id, namespace__org_id=org_id).all()
        for i in bindings:
            perms += i.role.permissions.all().values_list('content_type__app_label', 'codename')
        return self.format_perms(perms)

    def get_org_permissions(self, user_obj, org_id):
        perms = []
        if org_id == 'DEFAULT':
            return self.format_perms(perms)
        bindings = OrgRoleBinding.objects.filter(user=user_obj, org=org_id).all()
        for i in bindings:
            perms += i.role.permissions.all().values_list('content_type__app_label', 'codename')
        return self.format_perms(perms)

    def get_system_permissions(self, user_obj):
        perms = []
        bindings = SystemRoleBinding.objects.filter(user=user_obj).all()
        for i in bindings:
            perms += i.role.permissions.all().values_list('content_type__app_label', 'codename')
        return self.format_perms(perms)

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
        if not user_obj.is_active:
            return False

        scoped_perm = self.parse_perm(perm)
        namespace_id = scoped_perm.get('ns')
        org_id = scoped_perm.get('org')
        perm = scoped_perm.get('perm')
        if namespace_id:
            return perm in self.get_namespace_permissions(user_obj, namespace_id, org_id)
        if org_id:
            return perm in self.get_org_permissions(user_obj, org_id)
        return perm in self.get_system_permissions(user_obj)

    def has_module_perms(self, user_obj, app_label):
        return True
