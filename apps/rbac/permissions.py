from django.db import models
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import permissions
from accounts.models import Safe
from .models import Role, SafeRoleBinding


def convert_action(action):
    """ TODO: To do perfect """
    if action in ['get', 'list', 'retrieve']:
        return 'view'
    if action in ['update', 'bulk_update', 'partial_bulk_update', 'put']:
        return 'change'
    if action in ['delete', 'destroy', 'bulk_destroy']:
        return 'delete'
    if action in ['create', 'post']:
        return 'add'
    return action


def get_model(view):
    model = None
    if hasattr(view, 'model'):
        model = view.model
    elif hasattr(view, 'queryset') and hasattr(view.queryset, 'model'):
        model = view.queryset.model

    assert type(model) is models.base.ModelBase, f'Model {model} type is not ModelBase'
    return model


def get_model_name(view):
    model = get_model(view)
    model_name = model._meta.model_name
    return model_name


def get_model_app_label(view):
    model = get_model(view)
    app_label = model._meta.app_label
    return app_label


def get_model_content_type(view):
    model_name = get_model_name(view)
    app_label = get_model_app_label(view)
    content_type = ContentType.objects.get(app_label=app_label, model=model_name)
    return content_type


def construct_request_permission_codename(request, view):
    action = convert_action(view.action)
    model = get_model_name(view)
    codename = f'{action}_{model}'
    return codename


class SafeRolePermission(permissions.IsAuthenticated, permissions.BasePermission):

    def has_permission_for_safe(self, request, view, safe: Safe):
        safe_role_bindings = SafeRoleBinding.objects.filter(user=request.user, safe=safe)
        roles_ids = set(list(safe_role_bindings.values_list('role_id', flat=True)))
        if not roles_ids:
            return False

        permissions_ids = Role.objects.filter(id__in=roles_ids).values_list('permissions', flat=True)
        permissions_ids = set(list(permissions_ids))
        if not permissions_ids:
            return False

        codename = construct_request_permission_codename(request, view)
        content_type = get_model_content_type(view)
        has_permission = Permission.objects \
            .filter(id__in=permissions_ids, codename=codename, content_type=content_type) \
            .exists()
        if not has_permission:
            return False

        return True

    def has_permission(self, request, view):
        # create
        action = convert_action(view.action)
        if action == 'add':
            safe_id = request.data.get('safe')
        elif action == 'view':
            safe_id = request.query_params.get('safe')
        else:
            return True

        safe = get_object_or_404(Safe, id=safe_id)
        return self.has_permission_for_safe(request, view, safe)

    def has_object_permission(self, request, view, obj):
        assert hasattr(obj, 'safe'), f'{obj} object does not have `safe` attribute'
        return self.has_permission_for_safe(request, view, obj.safe)



