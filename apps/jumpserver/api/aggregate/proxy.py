# views.py

from urllib.parse import urlencode

import requests
from rest_framework.exceptions import NotFound, APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView

from .utils import get_full_resource_map

router = DefaultRouter()

BASE_URL = "http://localhost:8080"


class ProxyMixin(APIView):
    """
    通用资源代理 API，支持动态路径、自动文档生成
    """
    permission_classes = [IsAuthenticated]

    def _build_url(self, resource_name: str, pk: str = None, query_params=None):
        resource_map = get_full_resource_map()
        resource = resource_map.get(resource_name)
        if not resource:
            raise NotFound(f"Unknown resource: {resource_name}")

        base_path = resource['path']
        if pk:
            base_path += f"{pk}/"

        if query_params:
            base_path += f"?{urlencode(query_params)}"

        return f"{BASE_URL}{base_path}"

    def _proxy(self, request, resource: str, pk: str = None, action='list'):
        method = request.method.lower()
        if method not in ['get', 'post', 'put', 'patch', 'delete', 'options']:
            raise APIException("Unsupported method")

        if not resource or resource == '{resource}':
            if request.data:
                resource = request.data.get('resource')

        query_params = request.query_params.dict()
        if action == 'list':
            query_params['limit'] = 10

        url = self._build_url(resource, pk, query_params)
        headers = {k: v for k, v in request.headers.items() if k.lower() != 'host'}
        cookies = request.COOKIES
        body = request.body if method in ['post', 'put', 'patch'] else None

        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                cookies=cookies,
                data=body,
                timeout=10,
            )
            content_type = resp.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                data = resp.json()
            else:
                data = resp.text  # 或者 bytes：resp.content

            return Response(data=data, status=resp.status_code)
        except requests.RequestException as e:
            raise APIException(f"Proxy request failed: {str(e)}")
