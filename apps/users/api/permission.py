from collections import defaultdict
from common.permissions import IsOrgAdmin
from rest_framework import generics
from rest_framework.response import Response
from .mixins import UserQuerysetMixin
from rbac.models import SafeRoleBinding


class UserPermissionApi(UserQuerysetMixin, generics.ListAPIView):
    permission_classes = (IsOrgAdmin, )

    def list(self, request, *args, **kwargs):
        data = {
            'safe': self.get_safe_permissions(),
            # 'org': self.get_org_permissions(),
            # 'system': self.get_system_permissions(),
        }
        return Response(data)

    def get_safe_permissions(self):
        """
        [ {'safe_id': '', 'permissions': []}, {} ]
        """
        user = self.get_object()
        safes = {}
        safes_permissions_mapping = defaultdict(set)
        role_bindings = SafeRoleBinding.objects.filter(user=user)
        for role_binding in role_bindings:
            safe = role_binding.safe
            safes[str(safe.id)] = safe
            permissions = role_binding.role.get_permissions_display()
            safes_permissions_mapping[str(safe.id)].update(permissions)
        safe_perms = []
        for safe_id, permissions in safes_permissions_mapping.items():
            safe = safes[safe_id]
            safe_perm = {
                'safe_id': safe_id,
                'safe_name': safe.name,
                'permissions': permissions,
                'org_id': safe.org_id,
                'org_name': safe.org_name,
            }
            safe_perms.append(safe_perm)
        return safe_perms
