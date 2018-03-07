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
from common.utils import get_logger
from ..hands import IsSuperUser, IsSuperUserOrAppUser
from ..models import SystemUser
from .. import serializers
from ..tasks import push_system_user_to_assets_manual, \
    test_system_user_connectability_manual


logger = get_logger(__file__)
__all__ = [
    'SystemUserViewSet', 'SystemUserAuthInfoApi',
    'SystemUserPushApi', 'SystemUserTestConnectiveApi'
]


class SystemUserViewSet(BulkModelViewSet):
    """
    System user api set, for add,delete,update,list,retrieve resource
    """
    queryset = SystemUser.objects.all()
    serializer_class = serializers.SystemUserSerializer
    permission_classes = (IsSuperUserOrAppUser,)


class SystemUserAuthInfoApi(generics.RetrieveAPIView):
    """
    Get system user auth info
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsSuperUserOrAppUser,)

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        data = {
            'id': system_user.id,
            'name': system_user.name,
            'username': system_user.username,
            'password': system_user.password,
            'private_key': system_user.private_key,
        }
        return Response(data)


class SystemUserPushApi(generics.RetrieveAPIView):
    """
    Push system user to cluster assets api
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        push_system_user_to_assets_manual.delay(system_user)
        return Response({"msg": "Task created"})


class SystemUserTestConnectiveApi(generics.RetrieveAPIView):
    """
    Push system user to cluster assets api
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        test_system_user_connectability_manual.delay(system_user)
        return Response({"msg": "Task created"})