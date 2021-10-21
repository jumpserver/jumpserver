# -*- coding: utf-8 -*-
#
from rest_framework.response import Response

from .serializer import SerializerMixin
from .filter import ExtraFilterFieldsMixin
from .action import RenderToJsonMixin

__all__ = [
    'CommonApiMixin', 'PaginatedResponseMixin',
]


class PaginatedResponseMixin:
    def get_paginated_response_with_query_set(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CommonApiMixin(SerializerMixin, ExtraFilterFieldsMixin, RenderToJsonMixin):
    pass




