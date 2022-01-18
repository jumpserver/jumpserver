
from django.db.models import F, Value
from django.db.models.functions import Concat

from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import current_org
from .. import serializers
from ..models import RoleBinding, SystemRoleBinding, OrgRoleBinding

__all__ = ['RoleBindingViewSet', 'SystemRoleBindingViewSet', 'OrgRoleBindingViewSet']


class RoleBindingViewSet(OrgBulkModelViewSet):
    model = RoleBinding
    serializer_class = serializers.RoleBindingSerializer
    filterset_fields = [
        'scope', 'user', 'role', 'org',
        'user__name', 'user__username', 'role__name'
    ]
    search_fields = [
        'user__name', 'user__username', 'role__name'
    ]

    def get_queryset(self):
        queryset = super().get_queryset()\
            .prefetch_related('user', 'role') \
            .annotate(
                user_display=Concat(
                    F('user__name'), Value('('),
                    F('user__username'), Value(')')
                ),
                role_display=F('role__name')
            )
        return queryset


class SystemRoleBindingViewSet(RoleBindingViewSet):
    model = SystemRoleBinding
    serializer_class = serializers.SystemRoleBindingSerializer


class OrgRoleBindingViewSet(RoleBindingViewSet):
    model = OrgRoleBinding
    serializer_class = serializers.OrgRoleBindingSerializer

    def perform_bulk_create(self, serializer):
        validated_data = serializer.validated_data
        bindings = [
            OrgRoleBinding(role=d['role'], user=d['user'], org_id=current_org.id, scope='org')
            for d in validated_data
        ]
        OrgRoleBinding.objects.bulk_create(bindings, ignore_conflicts=True)
