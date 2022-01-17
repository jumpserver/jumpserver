from django.db.models import Count
from django.utils.translation import ugettext as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action

from common.drf.api import JMSModelViewSet
from ..serializers import RoleSerializer, RoleUserSerializer
from ..models import Role, SystemRole, OrgRole
from .permission import PermissionViewSet

__all__ = [
    'RoleViewSet', 'RolePermissionsViewSet',
    'SystemRoleViewSet', 'OrgRoleViewSet'
]


class RoleViewSet(JMSModelViewSet):
    queryset = Role.objects.all()
    serializer_classes = {
        'default': RoleSerializer,
        'users': RoleUserSerializer,
    }
    filterset_fields = ['name', 'scope', 'builtin']
    search_fields = filterset_fields
    rbac_perms = {
        'users': 'rbac.view_rolebinding'
    }

    def perform_destroy(self, instance):
        if instance.builtin:
            error = _("Internal role, can't be destroy")
            raise PermissionDenied(error)
        return super().perform_destroy(instance)

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance.builtin:
            error = _("Internal role, can't be update")
            raise PermissionDenied(error)
        return super().perform_update(serializer)

    def get_queryset(self):
        queryset = super().get_queryset()\
            .annotate(permissions_amount=Count('permissions'))
        return queryset

    @action(methods=['GET'], detail=True)
    def users(self, *args, **kwargs):
        role = self.get_object()
        queryset = role.users
        return self.get_paginated_response_with_query_set(queryset)


class SystemRoleViewSet(RoleViewSet):
    queryset = SystemRole.objects.all()


class OrgRoleViewSet(RoleViewSet):
    queryset = OrgRole.objects.all()


# Sub view set
class RolePermissionsViewSet(PermissionViewSet):
    rbac_perms = (
        ('get_tree', 'role.view_role'),
    )
    http_method_names = ['get', 'option']
    check_disabled = False

    def get_queryset(self):
        role_id = self.kwargs.get('role_pk')
        role = Role.objects.get(id=role_id)
        self.scope = role.scope
        self.check_disabled = role.builtin
        queryset = role.get_permissions()\
            .prefetch_related('content_type')
        return queryset
