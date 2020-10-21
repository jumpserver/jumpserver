# -*- coding: utf-8 -*-
#
from rest_framework import generics
from django.db.models import F, Value
from django.db.models import Q
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404

from assets.models import Node, Asset
from orgs.mixins.api import OrgRelationMixin
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import current_org
from common.permissions import IsOrgAdmin
from .. import serializers
from .. import models

__all__ = [
    'ApplicationPermissionUserRelationViewSet',
    'ApplicationPermissionUserGroupRelationViewSet',
    'ApplicationPermissionApplicationRelationViewSet',
    'ApplicationPermissionSystemUserRelationViewSet'
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
    filter_fields = [
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
    filter_fields = [
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
    filter_fields = [
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
    filter_fields = [
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
