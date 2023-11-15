from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination


class MaxLimitOffsetPagination(LimitOffsetPagination):
    max_limit = settings.MAX_LIMIT_PER_PAGE

    def paginate_queryset(self, queryset, request, view=None):
        if view and hasattr(view, 'page_max_limit'):
            self.max_limit = view.page_max_limit
        if view and hasattr(view, 'page_default_limit'):
            self.default_limit = view.page_default_limit
        return super().paginate_queryset(queryset, request, view)
