from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import permissions
from accounts.models import Safe
from .models import Role, SafeRoleBinding


def convert_action(action):
    if action in ['create']:
        return 'add'
    if action in ['list', 'retrieve']:
        return 'view'
    if action in ['update', 'partial_update', 'bulk_update', 'partial_bulk_update']:
        return 'change'
    if action in ['destroy', 'bulk_destroy']:
        return 'delete'
    return action


def get_model_content_type(view):
    model = view.model._meta.model_name
    app_label = view.model._meta.app_label
    content_type = ContentType.objects.get(app_label=app_label, model=model)
    return content_type


def construct_request_permission_codename(view):
    action = convert_action(view.action)
    model = view.model._meta.model_name
    codename = f'{action}_{model}'
    return codename


class SafeRolePermission(permissions.IsAuthenticated, permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert hasattr(obj, 'safe'), f'{obj} object does not have `safe` attribute'
        return self.has_safe_permission(request, view, obj.safe)

    @staticmethod
    def has_safe_permission(request, view, safe):
        if isinstance(safe, str):
            safe = get_object_or_404(Safe, id=safe)
        assert isinstance(safe, Safe), f'safe is not Safe instance: {safe}'
        safe_role_bindings = SafeRoleBinding.objects.filter(user=request.user, safe=safe)
        roles_ids = set(list(safe_role_bindings.values_list('role_id', flat=True)))
        if not roles_ids:
            return False

        permissions_ids = Role.objects.filter(id__in=roles_ids).values_list('permissions', flat=True)
        permissions_ids = set(list(permissions_ids))
        if not permissions_ids:
            return False

        codename = construct_request_permission_codename(view)
        content_type = get_model_content_type(view)
        has_permission = Permission.objects \
            .filter(id__in=permissions_ids, codename=codename, content_type=content_type) \
            .exists()

        return has_permission
