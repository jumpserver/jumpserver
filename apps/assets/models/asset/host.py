from assets.const import GATEWAY_NAME
from .common import Asset


class Host(Asset):
    pass

    @classmethod
    def get_gateway_queryset(cls):
        queryset = cls.objects.filter(
            platform__name=GATEWAY_NAME
        )
        return queryset
