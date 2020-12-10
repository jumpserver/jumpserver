# -*- coding: utf-8 -*-
#

import logging
from rest_framework import generics, status
from rest_framework.views import Response

from .. import serializers
from ..utils import ComponentsMetricsUtil
from common.permissions import IsAppUser, IsSuperUser

logger = logging.getLogger(__file__)

# generics.CreateAPIView

__all__ = [
    'ComponentsListAPIView', 'ComponentsStateAPIView', 'ComponentsMetricsAPIView'
]


class ComponentsListAPIView(generics.ListAPIView):
    """ 返回 core 服务状态列表，类似于 terminal 列表"""
    permission_classes = (IsSuperUser,)

    def list(self, request, *args, **kwargs):
        return Response()


class ComponentsStateAPIView(generics.CreateAPIView):
    """ koko, guacamole, omnidb 上报状态 """
    permission_classes = (IsAppUser,)
    serializer_class = serializers.ComponentsStateSerializer


class ComponentsMetricsAPIView(generics.GenericAPIView):
    """ 返回汇总组件指标数据 """
    permission_classes = (IsSuperUser,)

    def get(self, request, *args, **kwargs):
        component_type = request.query_params.get('type')
        util = ComponentsMetricsUtil(component_type)
        metrics = util.get_metrics()
        return Response(metrics, status=status.HTTP_200_OK)
