from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request

from assets.models import Node


class AssetLimitOffsetPagination(LimitOffsetPagination):
    """
    需要与 `assets.api.mixin.FilterAssetByNodeMixin` 配合使用
    """
    def get_count(self, queryset):
        """
        1. 如果查询节点下的所有资产，那 count 使用 Node.assets_amount
        2. 如果有其他过滤条件使用 super
        3. 如果只查询该节点下的资产使用 super
        """
        exclude_query_params = {
            self.limit_query_param,
            self.offset_query_param,
            'node', 'all', 'show_current_asset',
            'node_id', 'display', 'draw', 'fields_size',
        }

        for k, v in self._request.query_params.items():
            if k not in exclude_query_params and v is not None:
                return super().get_count(queryset)

        is_query_all = self._view.is_query_node_all_assets
        if is_query_all:
            node = self._view.node
            if not node:
                node = Node.org_root()
            return node.assets_amount
        return super().get_count(queryset)

    def paginate_queryset(self, queryset, request: Request, view=None):
        self._request = request
        self._view = view
        return super().paginate_queryset(queryset, request, view=None)
