# -*- coding: utf-8 -*-
#
from collections import defaultdict
from django.db.models import F, Value, Model
from django.db.models.signals import m2m_changed
from django.db.models.functions import Concat

from common.permissions import IsOrgAdmin
from common.utils import get_logger
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import current_org
from .. import models, serializers

__all__ = [
    'SystemUserAssetRelationViewSet', 'SystemUserNodeRelationViewSet',
    'SystemUserUserRelationViewSet', 'BaseRelationViewSet',
]

logger = get_logger(__name__)


class RelationMixin:
    model: Model

    def get_queryset(self):
        queryset = self.model.objects.all()
        if not current_org.is_root():
            org_id = current_org.org_id()
            queryset = queryset.filter(systemuser__org_id=org_id)

        queryset = queryset.annotate(systemuser_display=Concat(
            F('systemuser__name'), Value('('),
            F('systemuser__username'), Value(')')
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
        for system_user, object_ids in system_users_objects_map.items():
            logger.debug('System user relation changed, send m2m_changed signals')
            m2m_changed.send(
                sender=sender, instance=system_user, action='post_add',
                reverse=False, model=model, pk_set=set(object_ids)
            )

    def get_sender(self):
        return self.model

    def get_objects_attr(self):
        return models.Asset, 'asset'

    def perform_create(self, serializer):
        instance = serializer.save()
        self.send_post_add_signal(instance)
        return instance


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
        "systemuser__name", "systemuser__username",
    ]

    def get_objects_attr(self):
        return models.Asset, 'asset'

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            asset_display=Concat(F('asset__hostname'), Value('('), F('asset__ip'), Value(')'))
        )
        return queryset

    def perform_create(self, serializer):
        instance = super().perform_create(serializer)
        if isinstance(instance, list):
            authbooks = instance
        elif isinstance(instance, self.model):
            authbooks = [instance]
        else:
            authbooks = []

        # 特权用户和资产进行关联时，更新资产的特权用户为当前关联的系统用户
        assets_admin_user_mapper = {
            authbook.asset: authbook.systemuser for authbook in authbooks
            if authbook.systemuser.is_admin_user
        }
        self.update_assets_admin_user_if_need(assets_admin_user_mapper)

    @staticmethod
    def update_assets_admin_user_if_need(assets_admin_user_mapper):
        for asset, admin_user in assets_admin_user_mapper.items():
            asset.admin_user = admin_user
        assets = list(assets_admin_user_mapper.keys())
        models.Asset.objects.bulk_update(assets, fields=['admin_user'])


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
        queryset = queryset.annotate(node_key=F('node__key'))
        return queryset

    def perform_create(self, serializer):
        instance = super().perform_create(serializer)
        if isinstance(instance, list):
            nodes_systemusers = instance
        elif isinstance(instance, self.model):
            nodes_systemusers = [instance]
        else:
            nodes_systemusers = []
        self.update_node_assets_admin_user_if_need(nodes_systemusers)

    def update_node_assets_admin_user_if_need(self, nodes_systemusers):
        for node_systemuser in nodes_systemusers:
            if not node_systemuser.systemuser.is_admin_user:
                continue
            assets = node_systemuser.node.get_all_assets()
            admin_user = node_systemuser.systemuser
            self.update_assets_admin_user(assets, admin_user)

    @staticmethod
    def update_assets_admin_user(assets, admin_user):
        for asset in assets:
            asset.admin_user = admin_user
        models.Asset.objects.bulk_update(assets, fields=['admin_user'])


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

