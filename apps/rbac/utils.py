from collections import defaultdict
from rbac.models import RoleBinding, Role, Permission


class RBACPermissionUtil(object):

    @classmethod
    def get_user_permissions(cls, user):
        # 获取用户绑定的角色与组织
        roles_orgs = list(RoleBinding.objects.filter(user=user).values_list('role_id', 'org_id'))

        # 获取用户绑定的角色 与 权限的映射
        roles_ids = set([str(role_id) for role_id, org_id in roles_orgs])
        roles_perms = list(Role.permissions.through.objects
                           .filter(role__in=roles_ids).values_list('role_id', 'permission_id'))
        perms_ids = set([str(perm_id) for role_id, perm_id in roles_perms])
        perms = list(Permission.objects.filter(id__in=perms_ids).prefetch_related('content_type'))
        perms_map = {str(perm.id): perm for perm in perms}
        roles_perms_map = defaultdict(set)
        for role_id, perm_id in roles_perms:
            perm = perms_map[str(perm_id)]
            roles_perms_map[str(role_id)].add(perm)

        perms = set()
        for role_id, org_id in roles_orgs:
            for permission in roles_perms_map[str(role_id)]:
                _perm = permission.app_label_codename
                if org_id:
                    _perm = f'org:{org_id}|{_perm}'
                perms.add(_perm)
        return perms

    @classmethod
    def user_has_perm(cls, user, perm, obj=None):
        perms = cls.get_user_permissions(user)
        return perm in perms
