from django.db.models import F

from orgs.mixins.api import OrgBulkModelViewSet
from common.permissions import IsOrgAdmin
from ..models import AuthBook
from .. import serializers

__all__ = ['AccountViewSet']


class AccountViewSet(OrgBulkModelViewSet):
    model = AuthBook
    filterset_fields = ("username", "asset", "systemuser")
    search_fields = filterset_fields
    serializer_class = serializers.AccountSerializer
    permission_classes = (IsOrgAdmin,)

    def get_queryset(self):
        queryset = super().get_queryset()\
            .annotate(ip=F('asset__ip'))\
            .annotate(hostname=F('asset__hostname'))
        return queryset
