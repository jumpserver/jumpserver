import logging
from functools import reduce

from django.utils.translation import ugettext_lazy as _
from django.db.models import F

from common.db.models import ChoiceSet
from orgs.mixins.models import OrgModelMixin
from common.db import models
from common.utils import lazyproperty
from assets.models import Asset, SystemUser, Node, FamilyMixin

from .base import BasePermission


__all__ = [
    'AssetPermission', 'Action', 'PermNode', 'UserAssetGrantedTreeNodeRelation',
]

# 使用场景
logger = logging.getLogger(__name__)


class Action:
    NONE = 0

    CONNECT = 0b1
    UPLOAD = 0b1 << 1
    DOWNLOAD = 0b1 << 2
    CLIPBOARD_COPY = 0b1 << 3
    CLIPBOARD_PASTE = 0b1 << 4
    ALL = 0xff
    UPDOWNLOAD = UPLOAD | DOWNLOAD
    CLIPBOARD_COPY_PASTE = CLIPBOARD_COPY | CLIPBOARD_PASTE

    DB_CHOICES = (
        (ALL, _('All')),
        (CONNECT, _('Connect')),
        (UPLOAD, _('Upload file')),
        (DOWNLOAD, _('Download file')),
        (UPDOWNLOAD, _("Upload download")),
        (CLIPBOARD_COPY, _('Clipboard copy')),
        (CLIPBOARD_PASTE, _('Clipboard paste')),
        (CLIPBOARD_COPY_PASTE, _('Clipboard copy paste'))
    )

    NAME_MAP = {
        ALL: "all",
        CONNECT: "connect",
        UPLOAD: "upload_file",
        DOWNLOAD: "download_file",
        UPDOWNLOAD: "updownload",
        CLIPBOARD_COPY: 'clipboard_copy',
        CLIPBOARD_PASTE: 'clipboard_paste',
        CLIPBOARD_COPY_PASTE: 'clipboard_copy_paste'
    }

    NAME_MAP_REVERSE = {v: k for k, v in NAME_MAP.items()}
    CHOICES = []
    for i, j in DB_CHOICES:
        CHOICES.append((NAME_MAP[i], j))

    @classmethod
    def value_to_choices(cls, value):
        if isinstance(value, list):
            return value
        value = int(value)
        choices = [cls.NAME_MAP[i] for i, j in cls.DB_CHOICES if value & i == i]
        return choices

    @classmethod
    def value_to_choices_display(cls, value):
        choices = cls.value_to_choices(value)
        return [str(dict(cls.choices())[i]) for i in choices]
        
    @classmethod
    def choices_to_value(cls, value):
        if not isinstance(value, list):
            return cls.NONE
        db_value = [
            cls.NAME_MAP_REVERSE[v] for v in value
            if v in cls.NAME_MAP_REVERSE.keys()
        ]
        if not db_value:
            return cls.NONE

        def to_choices(x, y):
            return x | y

        result = reduce(to_choices, db_value)
        return result

    @classmethod
    def choices(cls):
        return [(cls.NAME_MAP[i], j) for i, j in cls.DB_CHOICES]


class AssetPermission(BasePermission):
    assets = models.ManyToManyField('assets.Asset', related_name='granted_by_permissions', blank=True, verbose_name=_("Asset"))
    nodes = models.ManyToManyField('assets.Node', related_name='granted_by_permissions', blank=True, verbose_name=_("Nodes"))
    system_users = models.ManyToManyField('assets.SystemUser', related_name='granted_by_permissions', verbose_name=_("System user"))
    actions = models.IntegerField(choices=Action.DB_CHOICES, default=Action.ALL, verbose_name=_("Actions"))

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Asset permission")
        ordering = ('name',)

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
        assets_ids = set(self.assets.all().values_list('id', flat=True))
        nodes_assets_ids = Node.get_nodes_all_assets_ids_by_keys(nodes_keys)
        assets_ids.update(nodes_assets_ids)
        assets = Asset.objects.filter(id__in=assets_ids)
        return assets


class UserAssetGrantedTreeNodeRelation(OrgModelMixin, FamilyMixin, models.JMSBaseModel):
    class NodeFrom(ChoiceSet):
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
