from common.permissions import SystemRBACPermission

from .utils import get_current_org


class OrgRBACPermission(SystemRBACPermission):

    @staticmethod
    def default_get_rbac_org_id(view):
        org_id = ''
        org = get_current_org()
        if org:
            org_id = org.id
        return org_id

    def get_org_id(self, view):
        if hasattr(view, 'get_rbac_org_id') and callable(view.get_rbac_org_id):
            org_id = view.get_rbac_org_id()
        else:
            org_id = self.default_get_rbac_org_id(view)
        return org_id

    def get_org_required_permissions(self, view, model_cls):
        perms = self.get_action_required_permissions(view, model_cls)
        org_id = self.get_org_id(view)
        perms = [f'org:{org_id}|{p}' for p in perms]
        return set(perms)

    def has_permission(self, request, view):
        if super().has_permission(request, view):
            return True
        if not self.user_is_valid(request):
            return False
        queryset = self._queryset(view)
        perms = self.get_org_required_permissions(view, queryset.model)
        return request.user.has_perms(perms)
