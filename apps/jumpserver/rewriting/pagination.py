from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination


class MaxLimitOffsetPagination(LimitOffsetPagination):
    max_limit = settings.MAX_LIMIT_PER_PAGE or 100
