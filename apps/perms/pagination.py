from rest_framework.request import Request

from assets.pagination import AssetPaginationBase
from common.utils import get_logger

logger = get_logger(__name__)


class GrantedAssetPaginationBase(AssetPaginationBase):
    _user: object

    def init_attrs(self, queryset, request: Request, view=None):
        super().init_attrs(queryset, request, view)
        self._user = view.user


class NodePermedAssetPagination(GrantedAssetPaginationBase):
    def get_count_from_nodes(self, queryset):
        return None


class AllPermedAssetPagination(GrantedAssetPaginationBase):
    def get_count_from_nodes(self, queryset):
        return None
