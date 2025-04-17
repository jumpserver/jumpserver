# -*- coding: utf-8 -*-
from django.db.models import Q

from common.api.generic import JMSBulkModelViewSet
from common.permissions import IsOwnerOrAdminWritable
from common.utils.http import is_true
from rbac.permissions import RBACPermission
from ..const import Scope
from ..models import AdHoc
from ..serializers import AdHocSerializer

__all__ = [
    'AdHocViewSet'
]


class AdHocViewSet(JMSBulkModelViewSet):
    queryset = AdHoc.objects.all()
    serializer_class = AdHocSerializer
    permission_classes = (RBACPermission, IsOwnerOrAdminWritable)
    search_fields = ('name', 'comment')
    filterset_fields = ['scope', 'creator']

    def allow_bulk_destroy(self, qs, filtered):
        for obj in filtered:
            self.check_object_permissions(self.request, obj)
        return True

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if is_true(self.request.query_params.get('only_mine')):
            queryset = queryset.filter(creator=user)
        else:
            queryset = queryset.filter(Q(creator=user) | Q(scope=Scope.public))
        return queryset
