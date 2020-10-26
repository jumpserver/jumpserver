from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from orgs.permissions import OrgRBACPermission


class NamespaceRBACPermission(OrgRBACPermission):
    @staticmethod
    def default_get_rbac_namespace_id(view):
        request = view.request
        if view.detail:
            obj = view.get_object()
            nid = obj.namespace.id
        else:
            nid = request.data.get('namespace', '') or request.query_params.get('namespace_id', '')
        if not nid:
            raise PermissionDenied
        return nid

    def get_namespace_id(self, view):
        if hasattr(view, 'get_rbac_namespace_id') and callable(view.get_rbac_namespace_id):
            namespace_id = view.get_rbac_namespace_id()
        else:
            namespace_id = self.default_get_rbac_namespace_id(view)
        return namespace_id

    def get_namespace_required_permissions(self, view, model_cls):
        perms = self.get_org_required_permissions(view, model_cls)
        namespace_id = self.get_namespace_id(view)
        perms = [f'ns:{namespace_id}|{p}' for p in perms]
        return set(perms)

    def has_permission(self, request, view):
        if super().has_permission(request, view):
            return True
        queryset = self._queryset(view)
        perms = self.get_namespace_required_permissions(view, queryset.model)
        return request.user.has_perms(perms)


class NamespacePermission(BasePermission):

    @staticmethod
    def has_handle_object_permission(request, view):
        if request.user.is_sys_admin:
            return True
        return False

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False
        if request.method in ['DELETE', 'PUT', 'PATCH', 'POST']:
            return self.has_handle_object_permission(request, view)
        return True
