from django.db.models import Q, Count
from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from common.api import JMSModelViewSet
from orgs.utils import current_org
from .permission import PermissionViewSet
from ..filters import RoleFilter
from ..models import Role, SystemRole, OrgRole, RoleBinding
from ..serializers import RoleSerializer, RoleUserSerializer

__all__ = [
    'RoleViewSet', 'SystemRoleViewSet', 'OrgRoleViewSet',
    'SystemRolePermissionsViewSet', 'OrgRolePermissionsViewSet',
]


class RoleViewSet(JMSModelViewSet):
    queryset = Role.objects.all()
    serializer_classes = {
        'default': RoleSerializer,
        'users': RoleUserSerializer,
    }
    ordering = ('-builtin', 'name')
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
        instance.permissions.set(clone.get_permissions())

    def filter_builtins(self, queryset):
        keyword = self.request.query_params.get('search')
        if not keyword:
            return queryset

        builtins = list(self.get_queryset().filter(builtin=True))
        matched = [role.id for role in builtins if keyword in role.display_name]
        if not matched:
            return queryset
        queryset = list(queryset.exclude(id__in=matched))
        return queryset + builtins

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = queryset.order_by(*self.ordering)
        queryset = self.filter_builtins(queryset)
        return queryset

    def set_users_amount(self, queryset):
        """设置角色的用户绑定数量，以减少查询"""
        ids = [role.id for role in queryset]
        queryset = Role.objects.filter(id__in=ids).order_by(*self.ordering)
        org_id = current_org.id
        q = Q(role__scope=Role.Scope.system) | Q(role__scope=Role.Scope.org, org_id=org_id)
        role_bindings = RoleBinding.objects.filter(q).values_list('role_id').annotate(
            user_count=Count('user_id', distinct=True)
        )
        role_user_amount_mapper = {role_id: user_count for role_id, user_count in role_bindings}
        queryset = queryset.annotate(permissions_amount=Count('permissions', distinct=True))
        queryset = list(queryset)
        for role in queryset:
            role.users_amount = role_user_amount_mapper.get(role.id, 0)
        return queryset

    def get_serializer(self, *args, **kwargs):
        if len(args) == 1 and kwargs.get('many', False):
            queryset = self.set_users_amount(args[0])
            args = (queryset,)
        return super().get_serializer(*args, **kwargs)

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance.builtin:
            error = _("Internal role, can't be update")
            raise PermissionDenied(error)
        return super().perform_update(serializer)

    @action(methods=['GET'], detail=True)
    def users(self, *args, **kwargs):
        role = self.get_object()
        queryset = role.users
        return self.get_paginated_response_from_queryset(queryset)


class SystemRoleViewSet(RoleViewSet):
    perm_model = SystemRole

    def get_queryset(self):
        qs = super().get_queryset().filter(scope='system')
        return qs


class OrgRoleViewSet(RoleViewSet):
    perm_model = OrgRole

    def get_queryset(self):
        qs = super().get_queryset().filter(scope='org')
        return qs


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
