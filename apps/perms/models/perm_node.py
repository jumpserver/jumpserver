from django.utils.translation import gettext_lazy as _

from accounts.models import Account
from assets.models import Asset, Node
from common.utils import lazyproperty


class PermNode(Node):
    class Meta:
        proxy = True
        ordering = []

    # 特殊节点
    UNGROUPED_NODE_KEY = 'ungrouped'
    UNGROUPED_NODE_VALUE = _('Ungrouped')
    FAVORITE_NODE_KEY = 'favorite'
    FAVORITE_NODE_VALUE = _('Favorite')

    def __str__(self):
        return f'{self.name}'

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
