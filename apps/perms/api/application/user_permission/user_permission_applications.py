# -*- coding: utf-8 -*-
#
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from applications.api.mixin import SerializeApplicationToTreeNodeMixin
from perms import serializers
from perms.api.asset.user_permission.mixin import ForAdminMixin, ForUserMixin
from perms.utils.application.user_permission import (
    get_user_granted_all_applications
)


__all__ = [
    'UserAllGrantedApplicationsApi',
    'MyAllGrantedApplicationsApi',
    'UserAllGrantedApplicationsAsTreeApi',
    'MyAllGrantedApplicationsAsTreeApi',
]


class AllGrantedApplicationsMixin(ListAPIView):
    only_fields = serializers.ApplicationGrantedSerializer.Meta.only_fields
    serializer_class = serializers.ApplicationGrantedSerializer
    filter_fields = ['id', 'name', 'comment']
    search_fields = ['name', 'comment']
    user: None

    def get_queryset(self):
        queryset = get_user_granted_all_applications(self.user)
        return queryset.only(*self.only_fields)


class UserAllGrantedApplicationsApi(ForAdminMixin, AllGrantedApplicationsMixin):
    only_fields = serializers.ApplicationGrantedSerializer.Meta.only_fields
    serializer_class = serializers.ApplicationGrantedSerializer
    filter_fields = ['id', 'name', 'comment']
    search_fields = ['name', 'comment']

    def get_queryset(self):
        queryset = get_user_granted_all_applications(self.user)
        return queryset.only(*self.only_fields)


class MyAllGrantedApplicationsApi(ForUserMixin, AllGrantedApplicationsMixin):
    pass


class ApplicationsAsTreeMixin(SerializeApplicationToTreeNodeMixin):
    """
    将应用序列化成树的结构返回
    """

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = self.serialize_applications(queryset)
        return Response(data=data)


class UserAllGrantedApplicationsAsTreeApi(ApplicationsAsTreeMixin, UserAllGrantedApplicationsApi):
    pass


class MyAllGrantedApplicationsAsTreeApi(ApplicationsAsTreeMixin, MyAllGrantedApplicationsApi):
    pass
