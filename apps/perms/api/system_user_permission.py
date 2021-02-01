from rest_framework import generics
from django.utils.decorators import method_decorator

from assets.models import SystemUser
from common.permissions import IsValidUser
from orgs.utils import tmp_to_root_org
from perms.utils.asset.user_permission import get_user_all_asset_perm_ids
from .. import serializers


@method_decorator(tmp_to_root_org(), name='list')
class SystemUserPermission(generics.ListAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.SystemUserSerializer

    def get_queryset(self):
        user = self.request.user

        asset_perms_id = get_user_all_asset_perm_ids(user)
        queryset = SystemUser.objects.filter(
            granted_by_permissions__id__in=asset_perms_id
        ).distinct()

        return queryset
