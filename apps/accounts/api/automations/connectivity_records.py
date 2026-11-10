from rest_framework import mixins

from accounts import serializers
from accounts.filters import ConnectivityRecordFilterSet
from accounts.models import ConnectivityRecord
from orgs.mixins.api import OrgGenericViewSet

__all__ = ['ConnectivityRecordViewSet']


class ConnectivityRecordViewSet(mixins.ListModelMixin, OrgGenericViewSet):
    model = ConnectivityRecord
    serializer_class = serializers.ConnectivityRecordSerializer
    filterset_class = ConnectivityRecordFilterSet
    search_fields = ('asset', 'asset_address', 'account', 'username', 'error')
    ordering_fields = ('asset', 'account', 'username', 'privileged', 'status', 'date_start', 'date_finished', 'id')
    ordering = ('-date_start', '-id')
    page_default_limit = 15
    http_method_names = ['get', 'head', 'options']
    rbac_perms = {
        'list': 'accounts.view_verifyaccountexecution | assets.view_pingexecution',
    }

    def get_queryset(self):
        permissions = {
            ConnectivityRecord.Type.asset: 'assets.view_pingexecution',
            ConnectivityRecord.Type.account: 'accounts.view_verifyaccountexecution',
        }
        allowed_types = [
            record_type for record_type, permission in permissions.items()
            if self.request.user.has_perm(permission)
        ]
        return super().get_queryset().filter(type__in=allowed_types)
