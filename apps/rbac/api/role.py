from django.utils.translation import ugettext_lazy as _
from common.drf.api import JMSBulkModelViewSet
from common.permissions import IsSuperUser
from common.exceptions import JMSException
from .. import serializers
from ..models import Role


__all__ = ['RoleViewSet']


class RoleViewSet(JMSBulkModelViewSet):
    permission_classes = (IsSuperUser, )
    serializer_class = serializers.RoleSerializer
    filterset_fields = ('display_name', 'name', 'type', 'is_builtin')
    search_fields = filterset_fields
    queryset = Role.objects.all()

    def perform_destroy(self, instance):
        if instance.is_builtin:
            error = _('Roles of built-in types are not allowed to be deleted')
            raise JMSException(error)
        return super().perform_destroy(instance)
