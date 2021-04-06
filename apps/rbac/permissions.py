from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import IsAuthenticated, BasePermission
from .models import Role, SafeRoleBinding


class SafeRolePermission(IsAuthenticated, BasePermission):

    def has_object_permission(self, request, view, obj):
        has_permission = self.check_user_permission(
            user=request.user, safe=obj.safe, model=view.model, view_action=view.action
        )
        return has_permission

    @classmethod
    def check_user_permission(cls, user, safe, model, view_action):
        # action + model -> codename
        # app + model -> content_type
        # User + Safe -> RoleBinding -> Role -> Permission
        # codename + content_type -> permission
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

        role_bindings = SafeRoleBinding.objects.filter(user=user, safe=safe)
        roles_ids = set(list(role_bindings.values_list('role_id', flat=True)))
        if not roles_ids:
            return False

        permissions = Role.permissions.through.objects.filter(role_id__in=roles_ids)
        permissions_ids = set(list(permissions.values_list('permission_id', flat=True)))
        if not permissions_ids:
            return False

        action = convert_action()
        codename = '{}_{}'.format(action, model._meta.model_name)
        content_type = ContentType.objects.get(
            app_label=model._meta.app_label, model=model._meta.model_name
        )
        has_permission = Permission.objects.filter(
            id__in=permissions_ids, codename=codename, content_type=content_type
        ).exists()
        return has_permission
