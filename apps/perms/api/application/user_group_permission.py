# -*- coding: utf-8 -*-
#

from django.db.models import Q
from rest_framework.generics import ListAPIView

from common.permissions import IsOrgAdminOrAppUser
from common.mixins.api import CommonApiMixin
from applications.models import Application
from perms import serializers

__all__ = [
    'UserGroupGrantedApplicationsApi'
]


class UserGroupGrantedApplicationsApi(CommonApiMixin, ListAPIView):
    """
    获取用户组直接授权的应用
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.ApplicationGrantedSerializer
    only_fields = serializers.ApplicationGrantedSerializer.Meta.only_fields
    filterset_fields = ['id', 'name', 'category', 'type', 'comment']
    search_fields = ['name', 'comment']

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        queryset = Application.objects\
            .filter(Q(granted_by_permissions__user_groups__id=user_group_id))\
            .distinct().only(*self.only_fields)
        return queryset
