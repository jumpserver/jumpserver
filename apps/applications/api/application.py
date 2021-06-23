# coding: utf-8
#

from orgs.mixins.api import OrgBulkModelViewSet

from ..hands import IsOrgAdminOrAppUser
from .. import serializers
from ..models import Application


__all__ = ['ApplicationViewSet']


class ApplicationViewSet(OrgBulkModelViewSet):
    model = Application
    filterset_fields = ('name', 'type', 'category')
    search_fields = filterset_fields
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.ApplicationSerializer
