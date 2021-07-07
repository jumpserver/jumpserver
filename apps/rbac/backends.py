from django.contrib.auth.backends import ModelBackend

from .models import RoleBinding


class RBACBackend(ModelBackend):
    @staticmethod
    def format_perms(perms):
        return ["%s.%s" % (ct, codename) for ct, codename in perms]

    def get_perms(self, user, org_id=None):
        # 系统角色绑定
        bindings = RoleBinding.objects.filter(user=user, org__isnull=True)
        # 组织角色绑定
        if org_id:
            bindings |= RoleBinding.objects.filter(user=user, org=org_id)

        perms = []
        for i in bindings:
            perms += list(i.role.get_permissions().values_list('content_type__app_label', 'codename'))
        return self.format_perms(perms)

    @staticmethod
    def parse_perm(perm):
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
        如: org:82364313-97f2-44ad-b206-17c94fa2a82c|accounts.create_account
        :param user_obj:
        :param perm: []
        :param obj:
        :return:
        """
        if not user_obj.is_active:
            return False

        scoped_perm = self.parse_perm(perm)
        org_id = scoped_perm.get('org')
        perm = scoped_perm.get('perm')

        perms = self.get_perms(user_obj, org_id)
        return perm in perms

    def has_module_perms(self, user_obj, app_label):
        return True
