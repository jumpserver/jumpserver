import uuid
import logging
from functools import reduce
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models import F, Q, TextChoices

from assets.models import Asset, Node, FamilyMixin, Account
from orgs.mixins.models import OrgModelMixin
from orgs.mixins.models import OrgManager
from common.utils import lazyproperty, date_expired_default
from common.db.models import BaseCreateUpdateModel, BitOperationChoice, UnionQuerySet

__all__ = [
    'AssetPermission', 'PermNode',
    'UserAssetGrantedTreeNodeRelation',
    'Action'
]

# 使用场景
logger = logging.getLogger(__name__)


class Action(BitOperationChoice):
    ALL = 0xff
    CONNECT = 0b1
    UPLOAD = 0b1 << 1
    DOWNLOAD = 0b1 << 2
    CLIPBOARD_COPY = 0b1 << 3
    CLIPBOARD_PASTE = 0b1 << 4
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


class AssetPermissionManager(OrgManager):
    def valid(self):
        return self.get_queryset().valid()


class AssetPermission(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    users = models.ManyToManyField('users.User', blank=True, verbose_name=_("User"),
                                   related_name='%(class)ss')
    user_groups = models.ManyToManyField('users.UserGroup', blank=True,
                                         verbose_name=_("User group"), related_name='%(class)ss')
    assets = models.ManyToManyField('assets.Asset', related_name='granted_by_permissions',
                                    blank=True, verbose_name=_("Asset"))
    nodes = models.ManyToManyField('assets.Node', related_name='granted_by_permissions', blank=True,
                                   verbose_name=_("Nodes"))
    # 只保存 @ALL (@INPUT @USER 默认包含，将来在全局设置中进行控制)
    # 特殊的账号描述
    # ['@ALL',]
    # 指定账号授权
    # ['web', 'root',]
    accounts = models.JSONField(default=list, verbose_name=_("Accounts"))
    actions = models.IntegerField(choices=Action.DB_CHOICES, default=Action.ALL,
                                  verbose_name=_("Actions"))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    date_start = models.DateTimeField(default=timezone.now, db_index=True,
                                      verbose_name=_("Date start"))
    date_expired = models.DateTimeField(default=date_expired_default, db_index=True,
                                        verbose_name=_('Date expired'))
    created_by = models.CharField(max_length=128, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    from_ticket = models.BooleanField(default=False, verbose_name=_('From ticket'))
    comment = models.TextField(verbose_name=_('Comment'), blank=True)

    objects = AssetPermissionManager.from_queryset(AssetPermissionQuerySet)()

    class SpecialAccount(models.TextChoices):
        ALL = '@ALL', 'All'
        INPUT = '@INPUT',  'Input'
        USER = '@USER', 'User'

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Asset permission")
        ordering = ('name',)
        permissions = []

    def __str__(self):
        return self.name

    @property
    def id_str(self):
        return str(self.id)

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

    @property
    def all_users(self):
        from users.models import User
        users_query = self._meta.get_field('users').related_query_name()
        user_groups_query = self._meta.get_field('user_groups').related_query_name()
        users_q = Q(**{f'{users_query}': self})
        user_groups_q = Q(**{f'groups__{user_groups_query}': self})
        return User.objects.filter(users_q | user_groups_q).distinct()

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

    @classmethod
    def get_queryset_with_prefetch(cls):
        return cls.objects.all().valid().prefetch_related(
            models.Prefetch('nodes', queryset=Node.objects.all().only('key')),
            models.Prefetch('assets', queryset=Asset.objects.all().only('id')),
        ).order_by()

    def get_all_assets(self, flat=False):
        from assets.models import Node
        nodes_keys = self.nodes.all().values_list('key', flat=True)
        asset_ids = set(self.assets.all().values_list('id', flat=True))
        nodes_asset_ids = Node.get_nodes_all_asset_ids_by_keys(nodes_keys)
        asset_ids.update(nodes_asset_ids)
        if flat:
            return asset_ids
        else:
            assets = Asset.objects.filter(id__in=asset_ids)
            return assets

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

    def get_asset_accounts(self):
        asset_ids = self.get_all_assets(flat=True)
        queries = Q(asset_id__in=asset_ids) \
                  & (Q(username__in=self.accounts) | Q(name__in=self.accounts))
        accounts = Account.objects.filter(queries)
        return accounts

    @classmethod
    def get_account_names(cls, perms):
        account_names = set()
        for perm in perms:
            perm: cls
            if not isinstance(perm.accounts, list):
                continue
            account_names.update(perm.accounts)
        return account_names

    @classmethod
    def filter_permissions(cls, user=None, asset=None, account=None):
        """ 获取同时包含 用户-资产-账号 的授权规则 """
        assetperm_ids = []
        if user:
            user_assetperm_ids = cls.filter_permissions_by_user(user, flat=True)
            assetperm_ids.append(user_assetperm_ids)
        if asset:
            asset_assetperm_ids = cls.filter_permissions_by_asset(asset, flat=True)
            assetperm_ids.append(asset_assetperm_ids)
        if account:
            account_assetperm_ids = cls.filter_permissions_by_account(account, flat=True)
            assetperm_ids.append(account_assetperm_ids)
        # & 是同时满足，比如有用户，但是用户的规则是空，那么返回也应该是空
        assetperm_ids = list(reduce(lambda x, y: set(x) & set(y), assetperm_ids))
        assetperms = cls.objects.filter(id__in=assetperm_ids).valid().order_by('-date_expired')
        return assetperms

    @classmethod
    def filter_permissions_by_user(cls, user, with_group=True, flat=False):
        assetperm_ids = set()
        user_assetperm_ids = AssetPermission.users.through.objects \
            .filter(user_id=user.id) \
            .values_list('assetpermission_id', flat=True) \
            .distinct()
        assetperm_ids.update(user_assetperm_ids)

        if with_group:
            usergroup_ids = user.get_groups(flat=True)
            usergroups_assetperm_id = AssetPermission.user_groups.through.objects \
                .filter(usergroup_id__in=usergroup_ids) \
                .values_list('assetpermission_id', flat=True) \
                .distinct()
            assetperm_ids.update(usergroups_assetperm_id)

        if flat:
            return assetperm_ids
        else:
            assetperms = cls.objects.filter(id__in=assetperm_ids).valid()
            return assetperms

    @classmethod
    def filter_permissions_by_asset(cls, asset, with_node=True, flat=False):
        assetperm_ids = set()
        asset_assetperm_ids = AssetPermission.assets.through.objects \
            .filter(asset_id=asset.id) \
            .values_list('assetpermission_id', flat=True)
        assetperm_ids.update(asset_assetperm_ids)

        if with_node:
            node_ids = asset.get_all_nodes(flat=True)
            node_assetperm_ids = AssetPermission.nodes.through.objects \
                .filter(node_id__in=node_ids) \
                .values_list('assetpermission_id', flat=True)
            assetperm_ids.update(node_assetperm_ids)

        if flat:
            return assetperm_ids
        else:
            assetperms = cls.objects.filter(id__in=assetperm_ids).valid()
            return assetperms

    @classmethod
    def filter_permissions_by_account(cls, account, flat=False):
        assetperms = cls.objects.filter(accounts__contains=account).valid()
        if flat:
            assetperm_ids = assetperms.values_list('id', flat=True)
            return assetperm_ids
        else:
            return assetperms


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
