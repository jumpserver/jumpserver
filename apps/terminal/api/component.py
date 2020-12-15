# -*- coding: utf-8 -*-
#

import logging
from rest_framework import generics, status
from rest_framework.views import Response

from .. import serializers
from ..utils import ComponentsMetricsUtil
from common.permissions import IsAppUser, IsSuperUser

logger = logging.getLogger(__file__)


__all__ = [
    'ComponentsStateAPIView', 'ComponentsMetricsAPIView',
]


class ComponentsStateAPIView(generics.CreateAPIView):
    """ koko, guacamole, omnidb 上报状态 """
    permission_classes = (IsAppUser,)
    serializer_class = serializers.ComponentsStateSerializer


class ComponentsMetricsAPIView(generics.GenericAPIView):
    """ 返回汇总组件指标数据 """
    permission_classes = (IsSuperUser,)

    def get(self, request, *args, **kwargs):
        tp = request.query_params.get('type')
        util = ComponentsMetricsUtil()
        metrics = util.get_metrics(tp)
        return Response(metrics, status=status.HTTP_200_OK)
