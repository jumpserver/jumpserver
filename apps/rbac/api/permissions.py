from rest_framework.viewsets import ReadOnlyModelViewSet
from django.contrib.auth.models import Permission
from common.permissions import IsSuperUser
from common.exceptions import JMSException
from ..models import RoleTypeChoices
from .. import serializers


__all__ = ['PermissionsViewSet']


class PermissionsViewSet(ReadOnlyModelViewSet):
    permission_classes = (IsSuperUser, )
    serializer_class = serializers.PermissionSerializer
    filterset_fields = ['id', 'name', 'content_type', 'codename']
    search_fields = filterset_fields
    queryset = Permission.objects.all()

    def filter_queryset(self, queryset):
        queryset = self.filter_role_type(queryset)
        queryset = queryset.order_by('content_type')
        return queryset

    def filter_role_type(self, queryset):
        role_type = self.request.query_params.get('role_type')
        if not role_type:
            return queryset
        if role_type not in RoleTypeChoices.names:
            raise JMSException('The query params `role_type` is invalid: {}'.format(role_type))
        queryset = RoleTypeChoices.get_permissions(tp=role_type)
        return queryset
