from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request

from common.utils import get_logger

logger = get_logger(__name__)


class GrantedAssetLimitOffsetPagination(LimitOffsetPagination):
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
        node = getattr(self._view, 'pagination_node', None)
        if node:
            logger.debug(f'Hit node.assets_amount[{node.assets_amount}] -> {self._request.get_full_path()}')
            return node.assets_amount
        else:
            logger.warn(f'Not hit node.assets_amount[{node.assets_amount}] because {self._view} not has `pagination_node` -> {self._request.get_full_path()}')
            return super().get_count(queryset)

    def paginate_queryset(self, queryset, request: Request, view=None):
        self._request = request
        self._view = view
        return super().paginate_queryset(queryset, request, view=None)
