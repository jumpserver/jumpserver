from rest_framework.decorators import action
from rest_framework.response import Response

from assets.models import Host, Asset
from assets.serializers import HostSerializer, HostInfoSerializer
from .asset import AssetViewSet

__all__ = ['HostViewSet']


class HostViewSet(AssetViewSet):
    model = Host
    perm_model = Asset

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = HostSerializer
        serializer_classes['info'] = HostInfoSerializer
        return serializer_classes

    @action(methods=["GET"], detail=True, url_path="info")
    def info(self, *args, **kwargs):
        asset = super().get_object()
        return Response(asset.info)
