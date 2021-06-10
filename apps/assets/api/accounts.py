
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics
from common.permissions import IsOrgAdmin

from ..models import AuthBook
from .. import serializers


class AccountViewSet(OrgBulkModelViewSet):
    model = AuthBook
    filterset_fields = ("username", "asset", "system_user")
    search_fields = filterset_fields
    serializer_class = serializers.AccountSerializer
    permission_classes = (IsOrgAdmin,)
