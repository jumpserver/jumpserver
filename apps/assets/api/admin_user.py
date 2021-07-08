from django.db.models import Count

from orgs.mixins.api import OrgBulkModelViewSet
from common.utils import get_logger
from ..hands import IsOrgAdmin
from ..models import SystemUser
from .. import serializers


logger = get_logger(__file__)
__all__ = ['AdminUserViewSet']


# 兼容一下老的 api
class AdminUserViewSet(OrgBulkModelViewSet):
    """
    Admin user api set, for add,delete,update,list,retrieve resource
    """
    model = SystemUser
    filterset_fields = ("name", "username")
    search_fields = filterset_fields
    serializer_class = serializers.AdminUserSerializer
    permission_classes = (IsOrgAdmin,)

    def get_queryset(self):
        queryset = super().get_queryset().filter(type=SystemUser.Type.admin)
        queryset = queryset.annotate(assets_amount=Count('assets'))
        return queryset
