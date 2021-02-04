# -*- coding: utf-8 -*-
#
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from common.mixins.api import CommonApiMixin
from applications.api.mixin import (
    SerializeApplicationToTreeNodeMixin
)
from perms import serializers
from perms.api.asset.user_permission.mixin import RoleAdminMixin, RoleUserMixin
from perms.utils.application.user_permission import (
    get_user_granted_all_applications
)


__all__ = [
    'UserAllGrantedApplicationsApi',
    'MyAllGrantedApplicationsApi',
    'UserAllGrantedApplicationsAsTreeApi',
    'MyAllGrantedApplicationsAsTreeApi',
]


class AllGrantedApplicationsMixin(CommonApiMixin, ListAPIView):
    only_fields = serializers.ApplicationGrantedSerializer.Meta.only_fields
    serializer_class = serializers.ApplicationGrantedSerializer
    filterset_fields = ['id', 'name', 'category', 'type', 'comment']
    search_fields = ['name', 'comment']
    user: None

    def get_queryset(self):
        queryset = get_user_granted_all_applications(self.user)
        return queryset.only(*self.only_fields)


class UserAllGrantedApplicationsApi(RoleAdminMixin, AllGrantedApplicationsMixin):
    pass


class MyAllGrantedApplicationsApi(RoleUserMixin, AllGrantedApplicationsMixin):
    pass


class ApplicationsAsTreeMixin(SerializeApplicationToTreeNodeMixin):
    """
    将应用序列化成树的结构返回
    """

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = self.serialize_applications_with_org(queryset)
        return Response(data=data)


class UserAllGrantedApplicationsAsTreeApi(ApplicationsAsTreeMixin, UserAllGrantedApplicationsApi):
    pass


class MyAllGrantedApplicationsAsTreeApi(ApplicationsAsTreeMixin, MyAllGrantedApplicationsApi):
    pass
