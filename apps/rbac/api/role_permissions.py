from rest_framework.viewsets import ReadOnlyModelViewSet
from django.contrib.auth.models import Permission
from common.permissions import IsSuperUser
from common.exceptions import JMSException
from ..models import RoleTypeChoices
from .. import serializers


__all__ = ['RolePermissionsViewSet']


class RolePermissionsViewSet(ReadOnlyModelViewSet):
    permission_classes = (IsSuperUser, )
    serializer_class = serializers.RolePermissionSerializer
    filterset_fields = ['id', 'name', 'content_type', 'codename']
    search_fields = filterset_fields

    def get_queryset(self):
        role_type = self.request.query_params.get('role_type')

        if role_type and role_type not in RoleTypeChoices.names:
            raise JMSException('The query params `role_type` is invalid: {}'.format(role_type))

        if role_type:
            queryset = RoleTypeChoices.get_permissions(tp=role_type)
        else:
            queryset = Permission.objects.all()

        return queryset.order_by('content_type')
