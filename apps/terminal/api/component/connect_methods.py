# -*- coding: utf-8 -*-
#
import itertools

from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.views import Response

from assets.models import Asset
from common.permissions import IsValidUser
from common.utils import distinct, get_request_os, is_true, is_uuid
from terminal import serializers
from terminal.connect_methods import ConnectMethodUtil

__all__ = ['ConnectMethodListApi']


class ConnectMethodListApi(generics.ListAPIView):
    serializer_class = serializers.ConnectMethodSerializer
    permission_classes = [IsValidUser]

    def get_queryset(self):
        os = self.request.query_params.get('os') or get_request_os(self.request)
        flat = self.request.query_params.get('flat')
        if is_true(flat):
            queryset = ConnectMethodUtil.get_filtered_protocols_connect_methods(os)
            queryset = itertools.chain.from_iterable(queryset.values())
            queryset = distinct(queryset, key=lambda x: x['value'])
        else:
            asset = None
            asset_id = self.request.query_params.get('asset_id')
            if asset_id:
                if not is_uuid(asset_id):
                    raise NotFound()
                asset = Asset.objects.filter(id=asset_id).first()
                if asset is None:
                    raise NotFound()
            queryset = ConnectMethodUtil.get_user_allowed_connect_methods(
                os, self.request.user, asset
            )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)
