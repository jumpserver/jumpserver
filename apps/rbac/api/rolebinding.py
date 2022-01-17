from django.db.models import F

from common.drf.api import JMSModelViewSet
from ..serializers import RoleBindingSerializer
from ..models import RoleBinding, SystemRoleBinding, OrgRoleBinding

__all__ = ['RoleBindingViewSet', 'SystemRoleBindingViewSet', 'OrgRoleBindingViewSet']


class RoleBindingViewSet(JMSModelViewSet):
    queryset = RoleBinding.objects.all()
    serializer_class = RoleBindingSerializer
    filterset_fields = ['scope', 'user', 'role', 'org']
    search_fields = filterset_fields

    def get_queryset(self):
        queryset = super().get_queryset()\
            .prefetch_related('user', 'role')\
            .annotate(
                user_display=F('user__name'),
                role_display=F('role__name')
            )
        return queryset


class SystemRoleBindingViewSet(RoleBindingViewSet):
    queryset = SystemRoleBinding.objects.all()


class OrgRoleBindingViewSet(RoleBindingViewSet):
    queryset = OrgRoleBinding.objects.all()

