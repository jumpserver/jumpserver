import logging
from functools import reduce

from django.utils.translation import ugettext_lazy as _
from django.db.models import F
from django.conf import settings

from common.db import models
from common.utils import lazyproperty
from assets.models import Asset, SystemUser, Node, FamilyMixin

from .base import BasePermission


__all__ = [
    'AssetPermission', 'Action', 'UserGrantedMappingNode', 'PermNode',
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
        nodes_assets_ids = Node.get_nodes_all_assets_ids(nodes_keys)
        assets_ids.update(nodes_assets_ids)
        assets = Asset.objects.filter(id__in=assets_ids)
        return assets


class UserGrantedMappingNode(FamilyMixin, models.JMSBaseModel):
    node = models.ForeignKey('assets.Node', default=None, on_delete=models.CASCADE,
                             db_constraint=False, null=True, related_name='mapping_nodes')
    key = models.CharField(max_length=64, verbose_name=_("Key"), db_index=True)  # '1:1:1:1'
    user = models.ForeignKey('users.User', db_constraint=False, on_delete=models.CASCADE)
    granted = models.BooleanField(default=False, db_index=True)
    asset_granted = models.BooleanField(default=False, db_index=True)
    parent_key = models.CharField(max_length=64, default='', verbose_name=_('Parent key'), db_index=True)  # '1:1:1:1'
    assets_amount = models.IntegerField(default=0)

    GRANTED_DIRECT = 1
    GRANTED_INDIRECT = 2
    GRANTED_NONE = 0

    @classmethod
    def get_node_granted_status(cls, key, user):
        ancestor_keys = Node.get_node_ancestor_keys(key, with_self=True)
        has_granted = UserGrantedMappingNode.objects.filter(
            key__in=ancestor_keys, user=user
        ).values_list('granted', flat=True)
        if not has_granted:
            return cls.GRANTED_NONE
        if any(list(has_granted)):
            return cls.GRANTED_DIRECT
        return cls.GRANTED_INDIRECT


class PermNode(Node):
    class Meta:
        proxy = True

    # 特殊节点
    UNGROUPED_NODE_KEY = 'ungrouped'
    UNGROUPED_NODE_VALUE = _('Ungrouped')
    FAVORITE_NODE_KEY = 'favorite'
    FAVORITE_NODE_VALUE = _('Favorite')

    # 节点授权状态
    GRANTED_DIRECT = 1
    GRANTED_INDIRECT = 2
    GRANTED_NONE = 0

    # 与 UserGrantedMappingNode 对应的字段，常用于 annotate
    is_granted = False
    is_asset_granted = False
    granted_assets_amount = 0

    annotate_mapping_node_fields = {
        'is_granted': F('mapping_nodes__granted'),
        'is_asset_granted': F('mapping_nodes__asset_granted'),
        'granted_assets_amount': F('mapping_nodes__assets_amount')
    }

    def use_mapping_assets_amount(self):
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
        return cls(
            id=cls.FAVORITE_NODE_KEY,
            key=cls.FAVORITE_NODE_KEY,
            value=cls.FAVORITE_NODE_VALUE,
            assets_amount=assets_amount
        )

    @classmethod
    def get_node_with_mapping_info(cls, user, id):
        queryset = cls.objects.filter(
            id=id,
            mapping_nodes__user=user
        ).annotate(**cls.annotate_mapping_node_fields)
        num = len(queryset)
        if num == 1:
            return queryset[0]
        if not num:
            raise cls.DoesNotExist(
                "%s matching query does not exist." %
                cls._meta.object_name
            )
        raise cls.MultipleObjectsReturned(
            'get() returned more than one %s -- it returned %s!' % (
                cls._meta.object_name,
                num,
            )
        )

    @classmethod
    def get_node_granted_status(cls, user, key):
        ancestor_keys = set(cls.get_node_ancestor_keys(key, with_self=True))
        ancestor_mapping_nodes = UserGrantedMappingNode.objects.filter(
            user=user,
            key__in=ancestor_keys
        ).only('key', 'granted')

        ancestor_mapping_nodes_keys = set()
        for mapping_node in ancestor_mapping_nodes:
            if mapping_node.granted:
                return cls.GRANTED_DIRECT
            ancestor_mapping_nodes_keys.add(mapping_node.key)

        if ancestor_keys != ancestor_mapping_nodes_keys:
            return cls.GRANTED_NONE
        return cls.GRANTED_INDIRECT

    def save(self):
        # 这是个只读 Model
        raise NotImplementedError
