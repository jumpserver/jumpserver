# -*- coding: utf-8 -*-
#
from collections import defaultdict
from django.db.models import F, Value
from django.db.models.signals import m2m_changed
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

    def send_post_add_signal(self, instance):
        if not isinstance(instance, list):
            instance = [instance]

        system_users_objects_map = defaultdict(list)
        model, object_field = self.get_objects_attr()

        for i in instance:
            _id = getattr(i, object_field).id
            system_users_objects_map[i.systemuser].append(_id)

        sender = self.get_sender()
        for system_user, objects in system_users_objects_map.items():
            m2m_changed.send(
                sender=sender, instance=system_user, action='post_add',
                reverse=False, model=model, pk_set=objects
            )

    def get_sender(self):
        return self.model

    def get_objects_attr(self):
        return models.Asset, 'asset'

    def perform_create(self, serializer):
        instance = serializer.save()
        self.send_post_add_signal(instance)


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

    def get_objects_attr(self):
        return models.Asset, 'asset'

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
        "node__value", "systemuser__name", "systemuser__username"
    ]

    def get_objects_attr(self):
        return models.Node, 'node'

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

    def get_objects_attr(self):
        from users.models import User
        return User, 'user'

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            user_display=Concat(
                F('user__name'), Value('('),
                F('user__username'), Value(')')
            )
        )
        return queryset

