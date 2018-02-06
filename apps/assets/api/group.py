# -*- coding: utf-8 -*-
#
# ~*~ coding: utf-8 ~*~
# Copyright (C) 2014-2018 Beijing DuiZhan Technology Co.,Ltd. All Rights Reserved.
#
# Licensed under the GNU General Public License v2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.gnu.org/licenses/gpl-2.0.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from rest_framework import generics
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet
from django.db.models import Count

from common.mixins import IDInFilterMixin
from common.utils import get_logger
from ..hands import IsSuperUser
from ..models import AssetGroup
from .. import serializers


logger = get_logger(__file__)

__all__ = [
    'AssetGroupViewSet', 'GroupUpdateAssetsApi', 'GroupAddAssetsApi'
]


class AssetGroupViewSet(IDInFilterMixin, BulkModelViewSet):
    """
    Asset group api set, for add,delete,update,list,retrieve resource
    """
    queryset = AssetGroup.objects.all().annotate(asset_count=Count("assets"))
    serializer_class = serializers.AssetGroupSerializer
    permission_classes = (IsSuperUser,)


class GroupUpdateAssetsApi(generics.RetrieveUpdateAPIView):
    """
    Asset group, update it's asset member
    """
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.GroupUpdateAssetsSerializer
    permission_classes = (IsSuperUser,)


class GroupAddAssetsApi(generics.UpdateAPIView):
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.GroupUpdateAssetsSerializer
    permission_classes = (IsSuperUser,)

    def update(self, request, *args, **kwargs):
        group = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data['assets']
            group.assets.add(*tuple(assets))
            return Response({"msg": "ok"})
        else:
            return Response({'error': serializer.errors}, status=400)