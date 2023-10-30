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
