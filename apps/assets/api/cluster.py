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


from common.mixins import IDInFilterMixin
from common.utils import get_logger
from ..hands import IsSuperUser
from ..models import Cluster
from .. import serializers
from ..tasks import test_admin_user_connectability_manual


logger = get_logger(__file__)
__all__ = [
    'ClusterViewSet', 'ClusterTestAssetsAliveApi', 'ClusterAddAssetsApi',
]


class ClusterViewSet(IDInFilterMixin, BulkModelViewSet):
    """
    Cluster api set, for add,delete,update,list,retrieve resource
    """
    queryset = Cluster.objects.all()
    serializer_class = serializers.ClusterSerializer
    permission_classes = (IsSuperUser,)


class ClusterTestAssetsAliveApi(generics.RetrieveAPIView):
    """
    Test cluster asset can connect using admin user or not
    """
    queryset = Cluster.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        cluster = self.get_object()
        admin_user = cluster.admin_user
        test_admin_user_connectability_manual.delay(admin_user)
        return Response("Task has been send, seen left assets status")


class ClusterAddAssetsApi(generics.UpdateAPIView):
    queryset = Cluster.objects.all()
    serializer_class = serializers.ClusterUpdateAssetsSerializer
    permission_classes = (IsSuperUser,)

    def update(self, request, *args, **kwargs):
        cluster = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data['assets']
            for asset in assets:
                asset.cluster = cluster
                asset.save()
            return Response({"msg": "ok"})
        else:
            return Response({'error': serializer.errors}, status=400)