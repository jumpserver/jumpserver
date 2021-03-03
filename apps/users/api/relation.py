# -*- coding: utf-8 -*-
#

from django.db.models import F

from common.drf.api import JMSBulkRelationModelViewSet
from common.permissions import IsOrgAdmin
from .. import serializers
from ..models import User

__all__ = ['UserUserGroupRelationViewSet']


class UserUserGroupRelationViewSet(JMSBulkRelationModelViewSet):
    filterset_fields = ('user', 'usergroup')
    search_fields = filterset_fields
    serializer_class = serializers.UserUserGroupRelationSerializer
    permission_classes = (IsOrgAdmin,)
    m2m_field = User.groups.field

    def get_queryset(self):
        return super().get_queryset().annotate(
            user_display=F('user__name'), usergroup_display=F('usergroup__name')
        )

    def allow_bulk_destroy(self, qs, filtered):
        if filtered.count() != 1:
            return False
        else:
            return True
