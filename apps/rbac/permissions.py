import json
from rest_framework.permissions import IsAuthenticated, BasePermission


class SafeRolePermission(IsAuthenticated, BasePermission):

    def has_object_permission(self, request, view, obj):
        has_permission = self.check_user_permission(
            user=request.user, safe=obj.safe, model=view.model, view_action=view.action
        )
        return has_permission

    @classmethod
    def check_user_permission(cls, user, safe, model, view_action):
        def convert_action():
            if view_action in ['create']:
                return 'add'
            if view_action in ['list', 'retrieve']:
                return 'view'
            if view_action in ['update', 'partial_update', 'bulk_update', 'partial_bulk_update']:
                return 'change'
            if view_action in ['destroy', 'bulk_destroy']:
                return 'delete'
            return view_action
        perm_dict = {
            'safe': str(safe.id), 'app_label': model._meta.app_label, 'action': convert_action(),
            'model_name': model._meta.model_name,
        }
        perm = json.dumps(perm_dict)
        return user.has_perm(perm)
