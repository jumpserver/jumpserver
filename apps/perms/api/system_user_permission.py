from rest_framework import generics

from assets.models import SystemUser
from common.permissions import IsValidUser
from perms.utils.asset.user_permission import get_user_all_asset_perm_ids
from .. import serializers


class SystemUserPermission(generics.ListAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.SystemUserSerializer

    def get_queryset(self):
        user = self.request.user

        asset_perm_ids = get_user_all_asset_perm_ids(user)
        queryset = SystemUser.objects.filter(
            granted_by_permissions__id__in=asset_perm_ids
        ).distinct()

        return queryset
