from rest_framework.generics import ListAPIView

from assets import serializers
from assets.const import Protocol
from common.permissions import IsValidUser

__all__ = ['ProtocolListApi']


class ProtocolListApi(ListAPIView):
    serializer_class = serializers.ProtocolSerializer
    permission_classes = (IsValidUser,)
    search_fields = ['label', 'value']

    def get_queryset(self):
        return list(Protocol.protocols())

    def filter_queryset(self, queryset):
        search = self.request.query_params.get('search')
        if search:
            fields = self.search_fields
            queryset = [
                item for item in queryset
                if any(search.lower() in str(getattr(item, field, '')).lower() for field in fields)
            ]
        return queryset
