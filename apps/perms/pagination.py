from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from django.db.models import Sum

from perms.models import UserAssetGrantedTreeNodeRelation
from common.utils import get_logger

logger = get_logger(__name__)


class GrantedAssetPaginationBase(LimitOffsetPagination):

    def paginate_queryset(self, queryset, request: Request, view=None):
        self._request = request
        self._view = view
        self._user = request.user
        return super().paginate_queryset(queryset, request, view=None)

    def get_count(self, queryset):
        exclude_query_params = {
            self.limit_query_param,
            self.offset_query_param,
            'key', 'all', 'show_current_asset',
            'cache_policy', 'display', 'draw',
            'order',
        }
        for k, v in self._request.query_params.items():
            if k not in exclude_query_params and v is not None:
                logger.warn(f'Not hit node.assets_amount because find a unknow query_param `{k}` -> {self._request.get_full_path()}')
                return super().get_count(queryset)
        return self.get_count_from_nodes(queryset)

    def get_count_from_nodes(self, queryset):
        raise NotImplementedError


class NodeGrantedAssetPagination(GrantedAssetPaginationBase):
    def get_count_from_nodes(self, queryset):
        node = getattr(self._view, 'pagination_node', None)
        if node:
            logger.debug(f'Hit node.assets_amount[{node.assets_amount}] -> {self._request.get_full_path()}')
            return node.assets_amount
        else:
            logger.warn(f'Not hit node.assets_amount[{node}] because {self._view} not has `pagination_node` -> {self._request.get_full_path()}')
            return super().get_count(queryset)


class AllGrantedAssetPagination(GrantedAssetPaginationBase):
    def get_count_from_nodes(self, queryset):
        assets_amount = sum(UserAssetGrantedTreeNodeRelation.objects.filter(
            user=self._user, node_parent_key=''
        ).values_list('node_assets_amount', flat=True))
        logger.debug(f'Hit all assets amount {assets_amount} -> {self._request.get_full_path()}')
        return assets_amount
