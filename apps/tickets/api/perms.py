from django.conf import settings

from assets.models import Asset, Node
from assets.serializers.asset.common import MiniAssetSerializer
from assets.serializers.node import NodeSerializer
from common.api import SuggestionMixin
from orgs.mixins.api import OrgReadonlyModelViewSet
from perms.utils import AssetPermissionPermAssetUtil
from perms.utils.permission import AssetPermissionUtil
from tickets.const import TicketApplyAssetScope

__all__ = ['ApplyAssetsViewSet', 'ApplyNodesViewSet']


class ApplyAssetsViewSet(OrgReadonlyModelViewSet, SuggestionMixin):
    model = Asset
    serializer_class = MiniAssetSerializer
    rbac_perms = (
        ("match", "assets.match_asset"),
    )

    search_fields = ("name", "address", "comment")

    def get_queryset(self):
        if TicketApplyAssetScope.is_permed():
            queryset = self.get_assets(with_expired=True)
        elif TicketApplyAssetScope.is_permed_valid():
            queryset = self.get_assets()
        else:
            queryset = super().get_queryset()
        return queryset

    def get_assets(self, with_expired=False):
        perms = AssetPermissionUtil().get_permissions_for_user(
            self.request.user, flat=True, with_expired=with_expired
        )
        util = AssetPermissionPermAssetUtil(perms)
        assets = util.get_all_assets()
        return assets


class ApplyNodesViewSet(OrgReadonlyModelViewSet, SuggestionMixin):
    model = Node
    serializer_class = NodeSerializer
    rbac_perms = (
        ("match", "assets.match_node"),
    )

    search_fields = ('full_value',)

    def get_queryset(self):
        if TicketApplyAssetScope.is_permed():
            queryset = self.get_nodes(with_expired=True)
        elif TicketApplyAssetScope.is_permed_valid():
            queryset = self.get_nodes()
        else:
            queryset = super().get_queryset()
        return queryset

    def get_nodes(self, with_expired=False):
        perms = AssetPermissionUtil().get_permissions_for_user(
            self.request.user, flat=True, with_expired=with_expired
        )
        util = AssetPermissionPermAssetUtil(perms)
        nodes = util.get_perm_nodes()
        return nodes
