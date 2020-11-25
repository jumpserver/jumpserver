# ~*~ coding: utf-8 ~*~
from common.permissions import IsOrgAdminOrAppUser
from common.drf.api import JMSBulkModelViewSet
from common.utils import get_logger
from . import serializers
from .models import Stat

logger = get_logger(__name__)
__all__ = ['StatViewSet']


class StatViewSet(JMSBulkModelViewSet):
    queryset = Stat.objects.all()
    filter_fields = ('id', 'key', 'value', 'component')
    search_fields = filter_fields
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.StatSerializer
