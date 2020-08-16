from rest_framework import generics
from django.db.models import Q
from django.utils.decorators import method_decorator

from assets.models import SystemUser
from common.permissions import IsValidUser
from orgs.utils import tmp_to_root_org
from .. import serializers


@method_decorator(tmp_to_root_org(), name='list')
class SystemUserPermission(generics.ListAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.SystemUserSerializer

    def get_queryset(self):
        user = self.request.user

        queryset = SystemUser.objects.filter(
            Q(granted_by_permissions__users=user) |
            Q(granted_by_permissions__user_groups__users=user)
        ).distinct()

        return queryset
