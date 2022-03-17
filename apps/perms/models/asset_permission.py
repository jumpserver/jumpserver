import logging

from django.utils.translation import ugettext_lazy as _
from django.db.models import F, TextChoices

from orgs.mixins.models import OrgModelMixin
from common.db import models
from common.utils import lazyproperty
from assets.models import Asset, SystemUser, Node, FamilyMixin

from .base import BasePermission


__all__ = [
    'AssetPermission', 'PermNode', 'UserAssetGrantedTreeNodeRelation',
]

# 使用场景
logger = logging.getLogger(__name__)


class AssetPermission(BasePermission):
    assets = models.ManyToManyField('assets.Asset', related_name='granted_by_permissions', blank=True, verbose_name=_("Asset"))
    nodes = models.ManyToManyField('assets.Node', related_name='granted_by_permissions', blank=True, verbose_name=_("Nodes"))
    system_users = models.ManyToManyField('assets.SystemUser', related_name='granted_by_permissions', blank=True, verbose_name=_("System user"))

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Asset permission")
        ordering = ('name',)
        permissions = [
        ]

    @lazyproperty
    def users_amount(self):
        return self.users.count()

    @lazyproperty
    def user_groups_amount(self):
        return self.user_groups.count()

    @lazyproperty
    def assets_amount(self):
        return self.assets.count()

    @lazyproperty
    def nodes_amount(self):
        return self.nodes.count()

    @lazyproperty
    def system_users_amount(self):
        return self.system_users.count()

    @classmethod
    def get_queryset_with_prefetch(cls):
        return cls.objects.all().valid().prefetch_related(
            models.Prefetch('nodes', queryset=Node.objects.all().only('key')),
            models.Prefetch('assets', queryset=Asset.objects.all().only('id')),
            models.Prefetch('system_users', queryset=SystemUser.objects.all().only('id'))
        ).order_by()

    def get_all_assets(self):
        from assets.models import Node
        nodes_keys = self.nodes.all().values_list('key', flat=True)
        asset_ids = set(self.assets.all().values_list('id', flat=True))
        nodes_asset_ids = Node.get_nodes_all_asset_ids_by_keys(nodes_keys)
        asset_ids.update(nodes_asset_ids)
        assets = Asset.objects.filter(id__in=asset_ids)
        return assets

    def users_display(self):
        names = [user.username for user in self.users.all()]
        return names

    def user_groups_display(self):
        names = [group.name for group in self.user_groups.all()]
        return names

    def assets_display(self):
        names = [asset.hostname for asset in self.assets.all()]
        return names

    def system_users_display(self):
        names = [system_user.name for system_user in self.system_users.all()]
        return names

    def nodes_display(self):
        names = [node.full_value for node in self.nodes.all()]
        return names


class UserAssetGrantedTreeNodeRelation(OrgModelMixin, FamilyMixin, models.JMSBaseModel):
    class NodeFrom(TextChoices):
        granted = 'granted', 'Direct node granted'
        child = 'child', 'Have children node'
        asset = 'asset', 'Direct asset granted'

    user = models.ForeignKey('users.User', db_constraint=False, on_delete=models.CASCADE)
    node = models.ForeignKey('assets.Node', default=None, on_delete=models.CASCADE,
                             db_constraint=False, null=False, related_name='granted_node_rels')
    node_key = models.CharField(max_length=64, verbose_name=_("Key"), db_index=True)
    node_parent_key = models.CharField(max_length=64, default='', verbose_name=_('Parent key'), db_index=True)
    node_from = models.CharField(choices=NodeFrom.choices, max_length=16, db_index=True)
    node_assets_amount = models.IntegerField(default=0)

    @property
    def key(self):
        return self.node_key

    @property
    def parent_key(self):
        return self.node_parent_key

    @classmethod
    def get_node_granted_status(cls, user, key):
        ancestor_keys = set(cls.get_node_ancestor_keys(key, with_self=True))
        ancestor_rel_nodes = cls.objects.filter(user=user, node_key__in=ancestor_keys)

        for rel_node in ancestor_rel_nodes:
            if rel_node.key == key:
                return rel_node.node_from, rel_node
            if rel_node.node_from == cls.NodeFrom.granted:
                return cls.NodeFrom.granted, None
        return '', None


class PermNode(Node):
    class Meta:
        proxy = True
        ordering = []

    # 特殊节点
    UNGROUPED_NODE_KEY = 'ungrouped'
    UNGROUPED_NODE_VALUE = _('Ungrouped')
    FAVORITE_NODE_KEY = 'favorite'
    FAVORITE_NODE_VALUE = _('Favorite')

    node_from = ''
    granted_assets_amount = 0

    annotate_granted_node_rel_fields = {
        'granted_assets_amount': F('granted_node_rels__node_assets_amount'),
        'node_from': F('granted_node_rels__node_from')
    }

    def use_granted_assets_amount(self):
        self.assets_amount = self.granted_assets_amount

    @classmethod
    def get_ungrouped_node(cls, assets_amount):
        return cls(
            id=cls.UNGROUPED_NODE_KEY,
            key=cls.UNGROUPED_NODE_KEY,
            value=cls.UNGROUPED_NODE_VALUE,
            assets_amount=assets_amount
        )

    @classmethod
    def get_favorite_node(cls, assets_amount):
        node = cls(
            id=cls.FAVORITE_NODE_KEY,
            key=cls.FAVORITE_NODE_KEY,
            value=cls.FAVORITE_NODE_VALUE,
        )
        node.assets_amount = assets_amount
        return node

    def get_granted_status(self, user):
        status, rel_node = UserAssetGrantedTreeNodeRelation.get_node_granted_status(user, self.key)
        self.node_from = status
        if rel_node:
            self.granted_assets_amount = rel_node.node_assets_amount
        return status

    def save(self):
        # 这是个只读 Model
        raise NotImplementedError


class PermedAsset(Asset):
    class Meta:
        proxy = True
        verbose_name = _('Permed asset')
        permissions = [
            ('view_myassets', _('Can view my assets')),
            ('view_userassets', _('Can view user assets')),
            ('view_usergroupassets', _('Can view usergroup assets')),
        ]

