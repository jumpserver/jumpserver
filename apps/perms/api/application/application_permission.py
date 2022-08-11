# -*- coding: utf-8 -*-
#
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView

from perms import serializers
from perms.models import ApplicationPermission
from applications.models import Application
from common.permissions import IsValidUser
from ..base import BasePermissionViewSet


class ApplicationPermissionViewSet(BasePermissionViewSet):
    """
    应用授权列表的增删改查API
    """
    model = ApplicationPermission
    serializer_class = serializers.ApplicationPermissionSerializer
    filterset_fields = {
        'name': ['exact'],
        'category': ['exact'],
        'type': ['exact', 'in'],
        'from_ticket': ['exact']
    }
    search_fields = ['name', 'category', 'type']
    custom_filter_fields = BasePermissionViewSet.custom_filter_fields + [
        'application_id', 'application', 'app', 'app_name'
    ]
    ordering_fields = ('name',)
    ordering = ('name',)

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            "applications", "users", "user_groups", "system_users"
        )
        return queryset

    def filter_application(self, queryset):
        app_id = self.request.query_params.get('application_id') or \
                 self.request.query_params.get('app')
        app_name = self.request.query_params.get('application') or \
                   self.request.query_params.get('app_name')

        if app_id:
            applications = Application.objects.filter(pk=app_id)
        elif app_name:
            applications = Application.objects.filter(name=app_name)
        else:
            return queryset
        if not applications:
            return queryset.none()
        queryset = queryset.filter(applications__in=applications)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_application(queryset)
        return queryset


class ApplicationPermissionActionsApi(RetrieveAPIView):
    permission_classes = (IsValidUser,)

    def retrieve(self, request, *args, **kwargs):
        category = request.GET.get('category')
        actions = ApplicationPermission.get_include_actions_choices(category=category)
        return Response(data=actions)
