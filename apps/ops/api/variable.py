# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.response import Response

from common.api.generic import JMSModelViewSet
from common.const.http import OPTIONS, GET
from common.permissions import IsValidUser
from ..models import Variable
from ..serializers import VariableSerializer, VariableFormDataSerializer

__all__ = [
    'VariableViewSet'
]


class VariableViewSet(JMSModelViewSet):
    queryset = Variable.objects.all()
    serializer_class = VariableSerializer
    http_method_names = ['options', 'get']

    @action(methods=[GET], detail=False, serializer_class=VariableFormDataSerializer,
            permission_classes=[IsValidUser, ], url_path='form_data')
    def form_data(self, request, *args, **kwargs):
        # 只是为了动态返回serializer fields info
        return Response({})
