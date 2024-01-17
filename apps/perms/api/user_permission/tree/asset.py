from django.conf import settings
from rest_framework.response import Response

from assets.api import SerializeToTreeNodeMixin
from assets.models import Asset
from common.utils import get_logger
from .mixin import RebuildTreeMixin
from ..assets import UserAllPermedAssetsApi

logger = get_logger(__name__)

__all__ = [
    'UserAllPermedAssetsAsTreeApi',
    'UserUngroupAssetsAsTreeApi',
]


class AssetTreeMixin(RebuildTreeMixin, SerializeToTreeNodeMixin):
    """ 将资产序列化成树节点的结构返回 """
    filter_queryset: callable
    get_queryset: callable

    ordering = ('name',)
    filterset_fields = ('id', 'name', 'address', 'comment')
    search_fields = ('name', 'address', 'comment')

    def list(self, request, *args, **kwargs):
        assets = self.filter_queryset(self.get_queryset())
        if request.query_params.get('search'):
            """ 限制返回数量, 搜索的条件不精准时，会返回大量的无意义数据 """
            assets = assets[:999]
        data = self.serialize_assets(assets, 'root')
        return Response(data=data)


class UserAllPermedAssetsAsTreeApi(AssetTreeMixin, UserAllPermedAssetsApi):
    """ 用户 '直接授权的资产' 作为树 """
    pass


class UserUngroupAssetsAsTreeApi(UserAllPermedAssetsAsTreeApi):
    """ 用户 '未分组节点的资产(直接授权的资产)' 作为树 """

    def get_assets(self):
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return super().get_assets()
        return Asset.objects.none()
