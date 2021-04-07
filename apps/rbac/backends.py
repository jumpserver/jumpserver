import json
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.contrib.auth.backends import ModelBackend
from .models import Role, SafeRoleBinding


class RBACBackends(ModelBackend):

    def has_perm(self, user_obj, perm, obj=None):
        """
        User -> RoleBinding -> Role -> Permission
        """
        perm_dict = json.loads(perm)
        org_id = perm_dict.get('org')
        safe_id = perm_dict.get('safe')
        app_label = perm_dict.get('app_label')
        action = perm_dict.get('action')
        model_name = perm_dict.get('model_name')
        if safe_id:
            role_bindings = SafeRoleBinding.objects.filter(user=user_obj, safe_id=safe_id)
        elif org_id:
            return False  # OrgRoleBinding
        else:
            return False  # SystemRoleBinding

        roles_ids = set(list(role_bindings.values_list('role_id', flat=True)))
        if not roles_ids:
            return False

        roles_permissions = Role.permissions.through.objects.filter(role_id__in=roles_ids)
        permissions_ids = set(list(roles_permissions.values_list('permission_id', flat=True)))
        if not permissions_ids:
            return False

        codename = '{}_{}'.format(action, model_name)
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        has_permission = Permission.objects.filter(
            id__in=permissions_ids, codename=codename, content_type=content_type
        ).exists()
        return has_permission

    def has_module_perms(self, user_obj, app_label):
        return True
