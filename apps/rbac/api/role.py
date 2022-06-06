from django.db.models import Count
from django.utils.translation import ugettext as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action

from common.drf.api import JMSModelViewSet
from ..filters import RoleFilter
from ..serializers import RoleSerializer, RoleUserSerializer
from ..models import Role, SystemRole, OrgRole
from .permission import PermissionViewSet
from common.mixins.api import PaginatedResponseMixin

__all__ = [
    'RoleViewSet', 'SystemRoleViewSet', 'OrgRoleViewSet',
    'SystemRolePermissionsViewSet', 'OrgRolePermissionsViewSet',
]


class RoleViewSet(PaginatedResponseMixin, JMSModelViewSet):
    queryset = Role.objects.all()
    serializer_classes = {
        'default': RoleSerializer,
        'users': RoleUserSerializer,
    }
    filterset_class = RoleFilter
    search_fields = ('name', 'scope', 'builtin')
    rbac_perms = {
        'users': 'rbac.view_rolebinding'
    }

    def perform_destroy(self, instance):
        from orgs.utils import tmp_to_root_org
        if instance.builtin:
            error = _("Internal role, can't be destroy")
            raise PermissionDenied(error)
        with tmp_to_root_org():
            if instance.users.count() >= 1:
                error = _("The role has been bound to users, can't be destroy")
                raise PermissionDenied(error)
        return super().perform_destroy(instance)

    def perform_create(self, serializer):
        super(RoleViewSet, self).perform_create(serializer)
        self.set_permissions_if_need(serializer.instance)

    def set_permissions_if_need(self, instance):
        if not isinstance(instance, Role):
            return
        clone_from = self.request.query_params.get('clone_from')
        if not clone_from:
            return
        clone = Role.objects.filter(id=clone_from).first()
        if not clone:
            return
        instance.permissions.set(clone.permissions.all())

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance.builtin:
            error = _("Internal role, can't be update")
            raise PermissionDenied(error)
        return super().perform_update(serializer)

    def get_queryset(self):
        queryset = super().get_queryset() \
            .annotate(permissions_amount=Count('permissions'))
        return queryset

    @action(methods=['GET'], detail=True)
    def users(self, *args, **kwargs):
        role = self.get_object()
        queryset = role.users
        return self.get_paginated_response_from_queryset(queryset)


class SystemRoleViewSet(RoleViewSet):
    queryset = SystemRole.objects.all()


class OrgRoleViewSet(RoleViewSet):
    queryset = OrgRole.objects.all()


class BaseRolePermissionsViewSet(PermissionViewSet):
    model = None
    role_pk = None
    filterset_fields = []
    http_method_names = ['get', 'option']
    check_disabled = False

    def get_queryset(self):
        role_id = self.kwargs.get(self.role_pk)
        if not role_id:
            return self.model.objects.none()

        role = self.model.objects.get(id=role_id)
        self.scope = role.scope
        self.check_disabled = role.builtin
        queryset = role.get_permissions() \
            .prefetch_related('content_type')
        return queryset


# Sub view set
class SystemRolePermissionsViewSet(BaseRolePermissionsViewSet):
    role_pk = 'system_role_pk'
    model = SystemRole
    rbac_perms = (
        ('get_tree', 'rbac.view_permission'),
    )


# Sub view set
class OrgRolePermissionsViewSet(BaseRolePermissionsViewSet):
    role_pk = 'org_role_pk'
    model = OrgRole
    rbac_perms = (
        ('get_tree', 'rbac.view_permission'),
    )

