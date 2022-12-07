from django.conf import settings
from rest_framework.request import Request

from assets.pagination import AssetPaginationBase
from perms.models import UserAssetGrantedTreeNodeRelation
from common.utils import get_logger

logger = get_logger(__name__)


class GrantedAssetPaginationBase(AssetPaginationBase):
    _user: object

    def init_attrs(self, queryset, request: Request, view=None):
        super().init_attrs(queryset, request, view)
        self._user = view.user


class NodePermedAssetPagination(GrantedAssetPaginationBase):
    def get_count_from_nodes(self, queryset):
        node = getattr(self._view, 'pagination_node', None)
        if node:
            logger.debug(f'Hit node.assets_amount[{node.assets_amount}] -> '
                         f'{self._request.get_full_path()}')
            return node.assets_amount
        else:
            logger.warn(f'Not hit node.assets_amount[{node}] because {self._view} '
                        f'not has `pagination_node` -> {self._request.get_full_path()}')
            return None


class AllPermedAssetPagination(GrantedAssetPaginationBase):
    def get_count_from_nodes(self, queryset):
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return None
        values = UserAssetGrantedTreeNodeRelation.objects.filter(
            user=self._user, node_parent_key=''
        ).values_list('node_assets_amount', flat=True)
        if not values:
            return None

        assets_amount = sum(values)
        logger.debug(f'Hit all assets amount {assets_amount} -> {self._request.get_full_path()}')
        return assets_amount
