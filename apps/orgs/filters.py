from django_filters.rest_framework import filters


class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    pass

