# -*- coding: utf-8 -*-
#
from django.db.models import F, Value
from django.db.models.functions import Concat

from common.permissions import IsOrgAdmin
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import current_org
from .. import models, serializers

__all__ = [
    'SystemUserAssetRelationViewSet', 'SystemUserNodeRelationViewSet',
    'SystemUserUserRelationViewSet',
]


class RelationMixin:
    def get_queryset(self):
        queryset = self.model.objects.all()
        org_id = current_org.org_id()
        if org_id is not None:
            queryset = queryset.filter(systemuser__org_id=org_id)
        queryset = queryset.annotate(systemuser_display=Concat(
            F('systemuser__name'), Value('('), F('systemuser__username'),
            Value(')')
        ))
        return queryset


class BaseRelationViewSet(RelationMixin, OrgBulkModelViewSet):
    pass


class SystemUserAssetRelationViewSet(BaseRelationViewSet):
    serializer_class = serializers.SystemUserAssetRelationSerializer
    model = models.SystemUser.assets.through
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', 'asset', 'systemuser',
    ]
    search_fields = [
        "id", "asset__hostname", "asset__ip",
        "systemuser__name", "systemuser__username"
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            asset_display=Concat(
                F('asset__hostname'), Value('('),
                F('asset__ip'), Value(')')
            )
        )
        return queryset


class SystemUserNodeRelationViewSet(BaseRelationViewSet):
    serializer_class = serializers.SystemUserNodeRelationSerializer
    model = models.SystemUser.nodes.through
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', 'node', 'systemuser',
    ]
    search_fields = [
        "node__value", "systemuser__name", "systemuser_username"
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset \
            .annotate(node_key=F('node__key'))
        return queryset


class SystemUserUserRelationViewSet(BaseRelationViewSet):
    serializer_class = serializers.SystemUserUserRelationSerializer
    model = models.SystemUser.users.through
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', 'user', 'systemuser',
    ]
    search_fields = [
        "user__username", "user__name",
        "systemuser__name", "systemuser__username",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            user_display=Concat(
                F('user__name'), Value('('),
                F('user__username'), Value(')')
            )
        )
        return queryset

