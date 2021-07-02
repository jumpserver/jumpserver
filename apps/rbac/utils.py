from collections import defaultdict
from orgs.models import Organization
from rbac.models import RoleBinding, Role, Permission
from rbac.const import ScopeChoices


class RBACPermissionUtil(object):

    @classmethod
    def get_user_permissions(cls, user):
        roles_orgs = list(RoleBinding.objects.filter(user=user).values_list('role_id', 'org_id'))
        roles_ids = [str(role_id) for role_id, org_id in roles_orgs]

        roles_perms = Role.permissions.through.objects.filter(role__in=roles_ids)
        roles_perms = list(roles_perms.values_list('role_id', 'permission_id'))

        perms_ids = [str(perm_id) for role_id, perm_id in roles_perms]
        perms = list(Permission.objects.filter(id__in=perms_ids).prefetch_related('content_type'))
        perms_map = {str(perm.id): perm for perm in perms}

        roles_perms_map = defaultdict(set)
        for role_id, perm_id in roles_perms:
            perm = perms_map[str(perm_id)]
            roles_perms_map[str(role_id)].add(perm)

        perms = set()
        for role_id, org_id, in roles_orgs:
            permissions = roles_perms_map[str(role_id)]
            for permission in permissions:
                _perm = permission.app_label_codename
                if org_id:
                    _perm = f'org:{org_id}|{_perm}'
                perms.add(_perm)
        return perms

    @classmethod
    def user_has_perm(cls, user, perm, obj=None):
        # 获取用户所有角色
        # 获取所有角色所有权限
        # 判断是否有某个权限
        perms = cls.get_user_permissions(user)
        return perm in perms
