from django.db.models import Count
from rest_framework.exceptions import PermissionDenied
from django.utils.translation import ugettext as _

from common.drf.api import JMSModelViewSet
from ..serializers import RoleSerializer, RoleBindingSerializer
from ..models import Role, RoleBinding
from .permission import PermissionViewSet

__all__ = ['RoleViewSet', 'RoleBindingViewSet', 'RolePermissionsViewSet']


class RoleViewSet(JMSModelViewSet):
    queryset = Role.objects.all()
    serializer_classes = {
        'default': RoleSerializer
    }
    filterset_fields = ['name', 'scope', 'builtin']
    search_fields = filterset_fields

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


class RoleBindingViewSet(JMSModelViewSet):
    queryset = RoleBinding.objects.all()
    serializer_class = RoleBindingSerializer
    filterset_fields = ['scope', 'user', 'role', 'org']
    search_fields = filterset_fields


class RolePermissionsViewSet(PermissionViewSet):
    action_perms_map = {
        'get_tree': 'role.view_role',
    }
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
