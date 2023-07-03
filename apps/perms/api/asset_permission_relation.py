# -*- coding: utf-8 -*-
#
from functools import lru_cache

from rest_framework import generics
from django.db.models import F
from django.shortcuts import get_object_or_404

from orgs.mixins.api import OrgRelationMixin
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import current_org
from perms import serializers
from perms import models
from perms.utils import AssetPermissionPermAssetUtil
from accounts.serializers import AccountSerializer

__all__ = [
    'AssetPermissionUserRelationViewSet', 'AssetPermissionUserGroupRelationViewSet',
    'AssetPermissionAssetRelationViewSet', 'AssetPermissionNodeRelationViewSet',
    'AssetPermissionAllAssetListApi', 'AssetPermissionAllUserListApi',
    'AssetPermissionAccountListApi',
]


class RelationMixin(OrgRelationMixin, OrgBulkModelViewSet):
    perm_model = models.AssetPermission

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
    filterset_fields = [
        'id', "user", "assetpermission",
    ]
    search_fields = ("user__name", "user__username", "assetpermission__name")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(user_display=F('user__name'))
        return queryset


class AssetPermissionAllUserListApi(generics.ListAPIView):
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
    filterset_fields = [
        'id', "usergroup", "assetpermission"
    ]
    search_fields = ["usergroup__name", "assetpermission__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(usergroup_display=F('usergroup__name'))
        return queryset


class AssetPermissionAssetRelationViewSet(RelationMixin):
    serializer_class = serializers.AssetPermissionAssetRelationSerializer
    m2m_field = models.AssetPermission.assets.field
    filterset_fields = [
        'id', 'asset', 'assetpermission',
    ]
    search_fields = ["id", "asset__name", "asset__address", "assetpermission__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(asset_display=F('asset__name'))
        return queryset


class AssetPermissionAllAssetListApi(generics.ListAPIView):
    serializer_class = serializers.AssetPermissionAllAssetSerializer
    filterset_fields = ("name", "address")
    search_fields = filterset_fields

    @lru_cache(maxsize=2)
    def get_queryset(self):
        pk = self.kwargs.get("pk")
        assets = AssetPermissionPermAssetUtil(perm_ids=[pk]).get_all_assets()
        return assets


class AssetPermissionNodeRelationViewSet(RelationMixin):
    serializer_class = serializers.AssetPermissionNodeRelationSerializer
    m2m_field = models.AssetPermission.nodes.field
    filterset_fields = [
        'id', 'node', 'assetpermission',
    ]
    search_fields = ["node__value", "assetpermission__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(node_key=F('node__key'))
        return queryset


class AssetPermissionAccountListApi(generics.ListAPIView):
    serializer_class = AccountSerializer
    filterset_fields = ("name", "username", "privileged", "version")
    search_fields = filterset_fields

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        perm = get_object_or_404(models.AssetPermission, pk=pk)
        accounts = perm.get_all_accounts()
        return accounts
