import uuid
import logging

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models import F, Q, TextChoices

from common.utils import lazyproperty, date_expired_default
from common.db.models import BaseCreateUpdateModel, UnionQuerySet
from assets.models import Asset, Node, FamilyMixin, Account
from orgs.mixins.models import OrgModelMixin
from orgs.mixins.models import OrgManager
from .const import Action, SpecialAccount

__all__ = [
    'AssetPermission', 'PermNode',
    'UserAssetGrantedTreeNodeRelation',
    'Action'
]

# 使用场景
logger = logging.getLogger(__name__)


class AssetPermissionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def valid(self):
        return self.active().filter(date_start__lt=timezone.now()) \
            .filter(date_expired__gt=timezone.now())

    def inactive(self):
        return self.filter(is_active=False)

    def invalid(self):
        now = timezone.now()
        q = (Q(is_active=False) | Q(date_start__gt=now) | Q(date_expired__lt=now))
        return self.filter(q)

    def filter_by_accounts(self, accounts):
        q = Q(accounts__contains=list(accounts)) | \
            Q(accounts__contains=SpecialAccount.ALL.value)
        return self.filter(q)


class AssetPermissionManager(OrgManager):
    def valid(self):
        return self.get_queryset().valid()


class AssetPermission(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    users = models.ManyToManyField(
        'users.User', related_name='%(class)ss', blank=True, verbose_name=_("User")
    )
    user_groups = models.ManyToManyField(
        'users.UserGroup', related_name='%(class)ss', blank=True, verbose_name=_("User group")
    )
    assets = models.ManyToManyField(
        'assets.Asset', related_name='granted_by_permissions', blank=True, verbose_name=_("Asset")
    )
    nodes = models.ManyToManyField(
        'assets.Node', related_name='granted_by_permissions', blank=True, verbose_name=_("Nodes")
    )
    # 特殊的账号: @ALL, @INPUT @USER 默认包含，将来在全局设置中进行控制.
    accounts = models.JSONField(default=list, verbose_name=_("Accounts"))
    actions = models.IntegerField(
        choices=Action.DB_CHOICES, default=Action.ALL, verbose_name=_("Actions")
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    date_start = models.DateTimeField(
        default=timezone.now, db_index=True, verbose_name=_("Date start")
    )
    date_expired = models.DateTimeField(
        default=date_expired_default, db_index=True, verbose_name=_('Date expired')
    )
    created_by = models.CharField(max_length=128, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    from_ticket = models.BooleanField(default=False, verbose_name=_('From ticket'))
    comment = models.TextField(verbose_name=_('Comment'), blank=True)

    objects = AssetPermissionManager.from_queryset(AssetPermissionQuerySet)()

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Asset permission")
        ordering = ('name',)
        permissions = []

    def __str__(self):
        return self.name

    @property
    def is_expired(self):
        if self.date_expired > timezone.now() > self.date_start:
            return False
        return True

    @property
    def is_valid(self):
        if not self.is_expired and self.is_active:
            return True
        return False

    def get_all_users(self):
        from users.models import User
        user_ids = self.users.all().values_list('id', flat=True)
        group_ids = self.user_groups.all().values_list('id', flat=True)
        user_ids = list(user_ids)
        group_ids = list(group_ids)
        qs1 = User.objects.filter(id__in=user_ids).distinct()
        qs2 = User.objects.filter(groups__id__in=group_ids).distinct()
        qs = UnionQuerySet(qs1, qs2)
        return qs

    def get_all_assets(self, flat=False):
        from assets.models import Node
        nodes_keys = self.nodes.all().values_list('key', flat=True)
        asset_ids = set(self.assets.all().values_list('id', flat=True))
        nodes_asset_ids = Node.get_nodes_all_asset_ids_by_keys(nodes_keys)
        asset_ids.update(nodes_asset_ids)
        if flat:
            return asset_ids
        assets = Asset.objects.filter(id__in=asset_ids)
        return assets

    def get_all_accounts(self, flat=False):
        """
         :return: 返回授权的所有账号对象 Account
        """
        asset_ids = self.get_all_assets(flat=True)
        q = Q(asset_id__in=asset_ids)
        if not self.is_perm_all_accounts:
            q &= Q(username__in=self.accounts)
        accounts = Account.objects.filter(q).order_by('asset__name', 'name', 'username')
        if not flat:
            return accounts
        return accounts.values_list('id', flat=True)

    @property
    def is_perm_all_accounts(self):
        return SpecialAccount.ALL in self.accounts

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

    def users_display(self):
        names = [user.username for user in self.users.all()]
        return names

    def user_groups_display(self):
        names = [group.name for group in self.user_groups.all()]
        return names

    def assets_display(self):
        names = [asset.name for asset in self.assets.all()]
        return names

    def nodes_display(self):
        names = [node.full_value for node in self.nodes.all()]
        return names


class UserAssetGrantedTreeNodeRelation(OrgModelMixin, FamilyMixin, BaseCreateUpdateModel):
    class NodeFrom(TextChoices):
        granted = 'granted', 'Direct node granted'
        child = 'child', 'Have children node'
        asset = 'asset', 'Direct asset granted'

    user = models.ForeignKey('users.User', db_constraint=False, on_delete=models.CASCADE)
    node = models.ForeignKey('assets.Node', default=None, on_delete=models.CASCADE,
                             db_constraint=False, null=False, related_name='granted_node_rels')
    node_key = models.CharField(max_length=64, verbose_name=_("Key"), db_index=True)
    node_parent_key = models.CharField(max_length=64, default='', verbose_name=_('Parent key'),
                                       db_index=True)
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
