# -*- coding: utf-8 -*-
#
from rest_framework import generics
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404

from applications.models import Application
from orgs.mixins.api import OrgRelationMixin
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import current_org
from common.permissions import IsOrgAdmin
from perms import serializers
from perms import models

__all__ = [
    'ApplicationPermissionUserRelationViewSet',
    'ApplicationPermissionUserGroupRelationViewSet',
    'ApplicationPermissionApplicationRelationViewSet',
    'ApplicationPermissionSystemUserRelationViewSet',
    'ApplicationPermissionAllApplicationListApi',
    'ApplicationPermissionAllUserListApi',
]


class RelationMixin(OrgRelationMixin, OrgBulkModelViewSet):
    def get_queryset(self):
        queryset = super().get_queryset()
        org_id = current_org.org_id()
        if org_id is not None:
            queryset = queryset.filter(applicationpermission__org_id=org_id)
        queryset = queryset.annotate(applicationpermission_display=F('applicationpermission__name'))
        return queryset


class ApplicationPermissionUserRelationViewSet(RelationMixin):
    serializer_class = serializers.ApplicationPermissionUserRelationSerializer
    m2m_field = models.ApplicationPermission.users.field
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', "user", "applicationpermission",
    ]
    search_fields = ("user__name", "user__username", "applicationpermission__name")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(user_display=F('user__name'))
        return queryset


class ApplicationPermissionUserGroupRelationViewSet(RelationMixin):
    serializer_class = serializers.ApplicationPermissionUserGroupRelationSerializer
    m2m_field = models.ApplicationPermission.user_groups.field
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', "usergroup", "applicationpermission"
    ]
    search_fields = ["usergroup__name", "applicationpermission__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(usergroup_display=F('usergroup__name'))
        return queryset


class ApplicationPermissionApplicationRelationViewSet(RelationMixin):
    serializer_class = serializers.ApplicationPermissionApplicationRelationSerializer
    m2m_field = models.ApplicationPermission.applications.field
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', 'application', 'applicationpermission',
    ]
    search_fields = ["id", "application__name", "applicationpermission__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(application_display=F('application__name'))
        return queryset


class ApplicationPermissionSystemUserRelationViewSet(RelationMixin):
    serializer_class = serializers.ApplicationPermissionSystemUserRelationSerializer
    m2m_field = models.ApplicationPermission.system_users.field
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', 'systemuser', 'applicationpermission',
    ]
    search_fields = [
        "applicactionpermission__name", "systemuser__name", "systemuser__username"
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset \
            .annotate(systemuser_display=Concat(
                F('systemuser__name'), Value('('), F('systemuser__username'),
                Value(')')
            ))
        return queryset


class ApplicationPermissionAllApplicationListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.ApplicationPermissionAllApplicationSerializer
    only_fields = serializers.ApplicationPermissionAllApplicationSerializer.Meta.only_fields
    filterset_fields = ('name',)
    search_fields = filterset_fields

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        perm = get_object_or_404(models.ApplicationPermission, pk=pk)
        applications = Application.objects.filter(granted_by_permissions=perm)\
            .only(*self.only_fields).distinct()
        return applications


class ApplicationPermissionAllUserListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.ApplicationPermissionAllUserSerializer
    only_fields = serializers.ApplicationPermissionAllUserSerializer.Meta.only_fields
    filterset_fields = ('username', 'name')
    search_fields = filterset_fields

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        perm = get_object_or_404(models.ApplicationPermission, pk=pk)
        users = perm.get_all_users().only(*self.only_fields).distinct()
        return users
