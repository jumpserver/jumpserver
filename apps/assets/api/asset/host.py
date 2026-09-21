from assets.models import Host, Asset
from assets.serializers import HostSerializer
from .asset import BaseAssetViewSet

__all__ = ['HostViewSet']


class HostViewSet(BaseAssetViewSet):
    model = Host
    perm_model = Asset
    chat_ai_operation_guidance = {
        'create': (
            'The address is the only irreducible value for a basic Linux host. '
            'Derive a concise name from it, resolve the Linux platform with an '
            'authorized platform list operation, and use Core defaults unless '
            'the user specified otherwise.'
        ),
    }

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = HostSerializer
        return serializer_classes
