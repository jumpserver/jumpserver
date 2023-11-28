from django.conf import settings
from django.core.exceptions import FieldError
from rest_framework.pagination import LimitOffsetPagination


class MaxLimitOffsetPagination(LimitOffsetPagination):
    max_limit = settings.MAX_LIMIT_PER_PAGE

    def get_count(self, queryset):
        try:
            return queryset.values_list('id').order_by().count()
        except (AttributeError, TypeError, FieldError):
            return len(queryset)
