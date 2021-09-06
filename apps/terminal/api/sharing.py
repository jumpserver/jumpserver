from rest_framework.mixins import CreateModelMixin
from rest_framework.exceptions import MethodNotAllowed

from common.permissions import IsAppUser, IsSuperUser
from orgs.mixins.api import OrgModelViewSet
from .. import serializers, models

__all__ = ['SessionSharingViewSet']


class SessionSharingViewSet(OrgModelViewSet):
    serializer_class = serializers.SessionSharingSerializer
    permission_classes = (IsAppUser | IsSuperUser, )
    search_fields = ('session', 'creator', 'is_active', 'expired_time')
    filterset_fields = search_fields
    model = models.SessionSharing

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)
