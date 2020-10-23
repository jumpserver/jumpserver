from orgs.permissions import OrgRBACPermission


class NamespaceRBACPermission(OrgRBACPermission):
    @staticmethod
    def default_get_rbac_namespace_id(view):
        action = getattr(view, 'action', '')
        request = view.request
        if action in ['update', 'retrieve', 'partial_update', 'destroy']:
            obj = view.get_object()
            return obj.namespace.id
        if action in ['create']:
            nid = request.data.get('namespace_id', '')
            return nid
        if action in ['list']:
            # nid = view.kwargs.get('nid', '')
            nid = request.query_params.get('namespace_id', '')
            return nid
        return ''

    def get_namespace_id(self, view):
        if hasattr(view, 'get_rbac_namespace_id') and callable(view.get_rbac_namespace_id):
            namespace_id = view.get_rbac_namespace_id()
        else:
            namespace_id = self.default_get_rbac_namespace_id(view)
        return namespace_id

    def get_namespace_required_permissions(self, view, model_cls):
        perms = self.get_action_required_permissions(view, model_cls)
        namespace_id = self.get_namespace_id(view)
        perms = [f'ns:{namespace_id}|{p}' for p in perms]
        return set(perms)

    def has_permission(self, request, view):
        if super().has_permission(request, view):
            return True
        queryset = self._queryset(view)
        perms = self.get_namespace_required_permissions(view, queryset.model)
        return request.user.has_perms(perms)
