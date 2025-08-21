from rest_framework.generics import ListAPIView

from assets import serializers
from assets.const import Protocol
from common.permissions import IsValidUser

__all__ = ['ProtocolListApi']


class ProtocolListApi(ListAPIView):
    serializer_class = serializers.ProtocolSerializer
    permission_classes = (IsValidUser,)

    def get_queryset(self):
        return list(Protocol.protocols())

    def filter_queryset(self, queryset):
        search = self.request.query_params.get("search", "").lower().strip()
        if not search:
            return queryset
        queryset = [
            p for p in queryset
            if search in p['label'].lower() or search in p['value'].lower()
        ]
        return queryset
