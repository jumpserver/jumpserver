import re

from django.conf import settings
from django.core.exceptions import FieldError
from rest_framework.pagination import LimitOffsetPagination


class MaxLimitOffsetPagination(LimitOffsetPagination):
    max_limit = settings.MAX_PAGE_SIZE
    default_limit = settings.DEFAULT_PAGE_SIZE
    _view = None
    _request = None

    def get_count(self, queryset):
        try:
            return queryset.values_list('id').order_by().count()
        except (AttributeError, TypeError, FieldError):
            return len(queryset)

    def paginate_queryset(self, queryset, request, view=None):
        # 保存 view 和 request 的引用，供 get_paginated_response_schema 使用
        self._view = view
        self._request = request
        
        if view and hasattr(view, 'page_max_limit'):
            self.max_limit = view.page_max_limit
        if view and hasattr(view, 'page_default_limit'):
            self.default_limit = view.page_default_limit

        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response_schema(self, schema):
        """
        生成分页响应 schema，使用当前视图的实际路径
        """
        # 获取当前路径
        base_path = self._get_current_path()
        base_url = self._get_base_url()
        
        return {
            'type': 'object',
            'properties': {
                'count': {
                    'type': 'integer',
                    'example': 123,
                },
                'next': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'example': f'{base_url}{base_path}?offset=400&limit=100'
                },
                'previous': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'example': f'{base_url}{base_path}?offset=200&limit=100'
                },
                'results': schema,
            },
        }
    
    def _get_current_path(self):
        return '/api/v1/app/models/'
    
    def _get_base_url(self):
        """
        获取基础 URL
        """
        if self._request:
            try:
                return f"{self._request.scheme}://{self._request.get_host()}"
            except Exception:
                pass
        
        return 'http://api.example.org'
