

from rest_framework import generics
from common.permissions import IsValidUser
from orgs.utils import tmp_to_root_org
from .. import serializers


class SystemUserPermission(generics.ListAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.SystemUserSerializer

    def get_queryset(self):
        return self.get_user_system_users()

    def get_user_system_users(self):
        from perms.utils import AssetPermissionUtil
        user = self.request.user
        with tmp_to_root_org():
            util = AssetPermissionUtil(user)
            return util.get_system_users()
