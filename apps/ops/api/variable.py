# -*- coding: utf-8 -*-
from common.api.generic import JMSBulkModelViewSet
from rbac.permissions import RBACPermission
from ..models import Variable
from ..serializers import VariableSerializer

__all__ = [
    'VariableViewSet'
]


class VariableViewSet(JMSBulkModelViewSet):
    queryset = Variable.objects.all()
    serializer_class = VariableSerializer
    permission_classes = (RBACPermission,)
