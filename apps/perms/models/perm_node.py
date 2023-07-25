from django.db import models
from django.db.models import F, TextChoices
from django.utils.translation import gettext_lazy as _

from accounts.models import Account
from assets.models import Asset, Node, FamilyMixin
from common.utils import lazyproperty
from orgs.mixins.models import JMSOrgBaseModel


class NodeFrom(TextChoices):
    granted = 'granted', 'Direct node granted'
    child = 'child', 'Have children node'
    asset = 'asset', 'Direct asset granted'


class UserAssetGrantedTreeNodeRelation(FamilyMixin, JMSOrgBaseModel):
    NodeFrom = NodeFrom

    id = models.AutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name=_('ID')
    )
    user = models.ForeignKey('users.User', db_constraint=False, on_delete=models.CASCADE)
    node = models.ForeignKey(
        'assets.Node', default=None, on_delete=models.CASCADE, db_constraint=False, null=False,
        related_name='granted_node_rels'
    )
    node_key = models.CharField(max_length=64, verbose_name=_("Key"), db_index=True)
    node_parent_key = models.CharField(
        max_length=64, default='', verbose_name=_('Parent key'), db_index=True
    )
    node_from = models.CharField(choices=NodeFrom.choices, max_length=16, db_index=True)
    node_assets_amount = models.IntegerField(default=0)
    comment = ''

    def __str__(self):
        return f'{self.user}|{self.node}'

    @property
    def key(self):
        return self.node_key

    @property
    def parent_key(self):
        return self.node_parent_key

    @classmethod
    def get_node_from_with_node(cls, user, key):
        ancestor_keys = set(cls.get_node_ancestor_keys(key, with_self=True))
        ancestor_nodes = cls.objects.filter(user=user, node_key__in=ancestor_keys)
        for node in ancestor_nodes:
            if node.key == key:
                return node.node_from, node
            if node.node_from == cls.NodeFrom.granted:
                return node.node_from, None
        return '', None


class PermNode(Node):
    NodeFrom = NodeFrom

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

    def __str__(self):
        return f'{self.name}'

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

    def compute_node_from_and_assets_amount(self, user):
        node_from, node = UserAssetGrantedTreeNodeRelation.get_node_from_with_node(
            user, self.key
        )
        self.node_from = node_from
        if node:
            self.granted_assets_amount = node.node_assets_amount

    def save(self):
        """ 这是个只读 Model """
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


class PermedAccount(Account):
    @lazyproperty
    def actions(self):
        return 0

    class Meta:
        proxy = True
        verbose_name = _('Permed account')
