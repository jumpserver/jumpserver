# -*- coding: utf-8 -*-
#

from django.db.models import Q
from rest_framework.generics import ListAPIView

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
    serializer_class = serializers.AppGrantedSerializer
    only_fields = serializers.AppGrantedSerializer.Meta.only_fields
    filterset_fields = ['id', 'name', 'category', 'type', 'comment']
    search_fields = ['name', 'comment']
    rbac_perms = {
        'list': 'perms.view_applicationpermission'
    }

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk')
        if not user_group_id:
            return Application.objects.none()

        queryset = Application.objects\
            .filter(Q(granted_by_permissions__user_groups__id=user_group_id))\
            .distinct().only(*self.only_fields)
        return queryset
