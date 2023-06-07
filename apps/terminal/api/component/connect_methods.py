# -*- coding: utf-8 -*-
#
import itertools

from rest_framework import generics
from rest_framework.views import Response

from common.permissions import IsValidUser
from common.utils import get_request_os, is_true, distinct
from terminal import serializers
from terminal.connect_methods import ConnectMethodUtil

__all__ = ['ConnectMethodListApi']


class ConnectMethodListApi(generics.ListAPIView):
    serializer_class = serializers.ConnectMethodSerializer
    permission_classes = [IsValidUser]

    def filter_user_connect_methods(self, d):
        from acls.models import ConnectMethodACL
        # 这里要根据用户来了，受 acl 影响
        acls = ConnectMethodACL.get_user_acls(self.request.user)
        disabled_connect_methods = acls.values_list('connect_methods', flat=True)
        disabled_connect_methods = set(itertools.chain.from_iterable(disabled_connect_methods))
        new_queryset = {}
        for protocol, methods in d.items():
            new_queryset[protocol] = [x for x in methods if x['value'] not in disabled_connect_methods]
        return new_queryset

    def get_queryset(self):
        os = self.request.query_params.get('os') or get_request_os(self.request)
        queryset = ConnectMethodUtil.get_filtered_protocols_connect_methods(os)
        flat = self.request.query_params.get('flat')

        # 先这么处理, 这里不用过滤包含的事所有
        if is_true(flat):
            queryset = itertools.chain.from_iterable(queryset.values())
            queryset = distinct(queryset, key=lambda x: x['value'])
        else:
            queryset = self.filter_queryset(queryset)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)
