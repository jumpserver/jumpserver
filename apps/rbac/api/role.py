from django.db.models import Count

from common.tree import TreeNodeSerializer
from common.drf.api import JMSModelViewSet
from common.permissions import IsSuperUser, IsOrgAdmin
from ..serializers import RoleSerializer, RoleBindingSerializer
from ..models import Role, RoleBinding

__all__ = ['RoleViewSet', 'RoleBindingViewSet']


class RoleViewSet(JMSModelViewSet):
    queryset = Role.objects.all()
    serializer_classes = {
        'get_tree': TreeNodeSerializer,
        'default': RoleSerializer
    }
    filterset_fields = ['name', 'scope', 'builtin']
    search_fields = filterset_fields
    permission_classes = (IsSuperUser, )

    def get_queryset(self):
        queryset = super().get_queryset()\
            .annotate(users_amount=Count('users')) \
            .annotate(permissions_amount=Count('permissions'))
        return queryset


class RoleBindingViewSet(JMSModelViewSet):
    queryset = RoleBinding.objects.all()
    serializer_class = RoleBindingSerializer
    filterset_fields = ['scope', 'user', 'role', 'org']
    search_fields = filterset_fields
    permission_classes = (IsOrgAdmin, )
