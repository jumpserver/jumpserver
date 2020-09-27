from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request


class GrantedAssetLimitOffsetPagination(LimitOffsetPagination):
    def get_count(self, queryset):
        exclude_query_params = {
            self.limit_query_param,
            self.offset_query_param,
            'key', 'all', 'show_current_asset',
            'cache_policy', 'display', 'draw'
        }
        has_filter = False
        for k, v in self._request.query_params.items():
            if k not in exclude_query_params and v is not None:
                has_filter = True
                break
        if has_filter:
            return super().get_count(queryset)
        node = self._view.node
        return node.assets_amount

    def paginate_queryset(self, queryset, request: Request, view=None):
        self._request = request
        self._view = view
        return super().paginate_queryset(queryset, request, view=None)
