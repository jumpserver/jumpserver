# -*- coding: utf-8 -*-
#
from applications.models import Application
from perms.models import ApplicationPermission
from perms import serializers
from ..base import BasePermissionViewSet


class ApplicationPermissionViewSet(BasePermissionViewSet):
    """
    应用授权列表的增删改查API
    """
    model = ApplicationPermission
    serializer_class = serializers.ApplicationPermissionSerializer
    filterset_fields = ['name', 'category', 'type']
    search_fields = filterset_fields
    custom_filter_fields = BasePermissionViewSet.custom_filter_fields + [
        'application_id', 'application'
    ]

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            "applications", "users", "user_groups", "system_users"
        )
        return queryset

    def filter_application(self, queryset):
        application_id = self.request.query_params.get('application_id')
        application_name = self.request.query_params.get('application')
        if application_id:
            applications = Application.objects.filter(pk=application_id)
        elif application_name:
            applications = Application.objects.filter(name=application_name)
        else:
            return queryset
        if not applications:
            return queryset.none()
        queryset = queryset.filter(applications=applications)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_application(queryset)
        return queryset

