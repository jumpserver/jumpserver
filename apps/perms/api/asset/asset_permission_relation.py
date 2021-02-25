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
from perms import serializers
from perms import models
from perms.utils.asset.user_permission import UserGrantedAssetsQueryUtils

__all__ = [
    'AssetPermissionUserRelationViewSet', 'AssetPermissionUserGroupRelationViewSet',
    'AssetPermissionAssetRelationViewSet', 'AssetPermissionNodeRelationViewSet',
    'AssetPermissionSystemUserRelationViewSet', 'AssetPermissionAllAssetListApi',
    'AssetPermissionAllUserListApi',
]


class RelationMixin(OrgRelationMixin, OrgBulkModelViewSet):
    def get_queryset(self):
        queryset = super().get_queryset()
        org_id = current_org.org_id()
        if org_id is not None:
            queryset = queryset.filter(assetpermission__org_id=org_id)
        queryset = queryset.annotate(assetpermission_display=F('assetpermission__name'))
        return queryset


class AssetPermissionUserRelationViewSet(RelationMixin):
    serializer_class = serializers.AssetPermissionUserRelationSerializer
    m2m_field = models.AssetPermission.users.field
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', "user", "assetpermission",
    ]
    search_fields = ("user__name", "user__username", "assetpermission__name")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset \
            .annotate(user_display=F('user__name'))
        return queryset


class AssetPermissionAllUserListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionAllUserSerializer
    filterset_fields = ("username", "name")
    search_fields = filterset_fields

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        perm = get_object_or_404(models.AssetPermission, pk=pk)
        users = perm.get_all_users().only(
            *self.serializer_class.Meta.only_fields
        )
        return users


class AssetPermissionUserGroupRelationViewSet(RelationMixin):
    serializer_class = serializers.AssetPermissionUserGroupRelationSerializer
    m2m_field = models.AssetPermission.user_groups.field
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', "usergroup", "assetpermission"
    ]
    search_fields = ["usergroup__name", "assetpermission__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset \
            .annotate(usergroup_display=F('usergroup__name'))
        return queryset


class AssetPermissionAssetRelationViewSet(RelationMixin):
    serializer_class = serializers.AssetPermissionAssetRelationSerializer
    m2m_field = models.AssetPermission.assets.field
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', 'asset', 'assetpermission',
    ]
    search_fields = ["id", "asset__hostname", "asset__ip", "assetpermission__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset \
            .annotate(asset_display=F('asset__hostname'))
        return queryset


class AssetPermissionAllAssetListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionAllAssetSerializer
    filterset_fields = ("hostname", "ip")
    search_fields = filterset_fields

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        query_utils = UserGrantedAssetsQueryUtils(None, asset_perm_ids=[pk])
        assets = query_utils.get_all_granted_assets()
        return assets


class AssetPermissionNodeRelationViewSet(RelationMixin):
    serializer_class = serializers.AssetPermissionNodeRelationSerializer
    m2m_field = models.AssetPermission.nodes.field
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', 'node', 'assetpermission',
    ]
    search_fields = ["node__value", "assetpermission__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset \
            .annotate(node_key=F('node__key'))
        return queryset


class AssetPermissionSystemUserRelationViewSet(RelationMixin):
    serializer_class = serializers.AssetPermissionSystemUserRelationSerializer
    m2m_field = models.AssetPermission.system_users.field
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', 'systemuser', 'assetpermission',
    ]
    search_fields = [
        "assetpermission__name", "systemuser__name", "systemuser__username"
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset \
            .annotate(systemuser_display=Concat(
                F('systemuser__name'), Value('('), F('systemuser__username'),
                Value(')')
            ))
        return queryset
