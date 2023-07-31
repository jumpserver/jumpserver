from django.db.models import F, Value
from django.db.models.functions import Concat
from django.utils.translation import gettext as _

from common.exceptions import JMSException
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import current_org
from .. import serializers
from ..models import RoleBinding, SystemRoleBinding, OrgRoleBinding

__all__ = [
    'RoleBindingViewSet', 'SystemRoleBindingViewSet',
    'OrgRoleBindingViewSet'
]


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
        queryset = self._get_queryset() \
            .prefetch_related('user', 'role', 'org')
        return queryset

    def _get_queryset(self):
        return super().get_queryset()


class SystemRoleBindingViewSet(RoleBindingViewSet):
    model = SystemRoleBinding
    serializer_class = serializers.SystemRoleBindingSerializer

    def perform_destroy(self, instance):
        user = instance.user
        role_qs = self.model.objects.filter(user=user)
        if role_qs.count() == 1:
            msg = _('{} at least one system role').format(user)
            raise JMSException(code='system_role_delete_error', detail=msg)
        return super().perform_destroy(instance)


class OrgRoleBindingViewSet(RoleBindingViewSet):
    serializer_class = serializers.OrgRoleBindingSerializer

    def _get_queryset(self):
        return OrgRoleBinding.objects.root_all()

    def perform_bulk_create(self, serializer):
        validated_data = serializer.validated_data
        bindings = [
            OrgRoleBinding(
                role=d['role'], user=d['user'],
                org_id=current_org.id, scope='org'
            )
            for d in validated_data
        ]
        OrgRoleBinding.objects.bulk_create(bindings, ignore_conflicts=True)
