from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import OnlySuperUser
from common.utils import get_logger
from terminal import serializers
from terminal.mixin import LokiMixin

__all__ = ['LokiLogAPI', ]

logger = get_logger(__name__)


class LokiLogAPI(APIView, LokiMixin):
    http_method_names = ['get', ]
    permission_classes = [OnlySuperUser]

    def get(self, request, *args, **kwargs):
        serializer = serializers.LokiLogSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        components = serializer.validated_data.get('components')
        search = serializer.validated_data.get('search', '')
        start = serializer.validated_data.get('start', )
        end = serializer.validated_data.get('end', )
        loki_logs = self.query_components_log(components, search, start, end)
        return Response(data=loki_logs)

    def query_components_log(self, components, search, start, end):
        # 秒转纳秒
        start_ns = int(start * 1e9)
        end_ns = int(end * 1e9)
        query = self.create_loki_query(components, search)
        loki_client = self.get_loki_client()
        loki_response = loki_client.query_range(query, start_ns, end_ns, limit=100)
        return loki_response['data']['result']
