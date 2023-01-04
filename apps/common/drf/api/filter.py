# -*- coding: utf-8 -*-
#
from itertools import chain

from rest_framework.settings import api_settings

from common.drf.filters import IDSpmFilter, CustomFilter, IDInFilter


__all__ = ['ExtraFilterFieldsMixin']


class ExtraFilterFieldsMixin:
    """
    额外的 api filter
    """
    default_added_filters = [CustomFilter, IDSpmFilter, IDInFilter]
    filter_backends = api_settings.DEFAULT_FILTER_BACKENDS
    extra_filter_fields = []
    extra_filter_backends = []

    def get_filter_backends(self):
        if self.filter_backends != self.__class__.filter_backends:
            return self.filter_backends
        backends = list(chain(
            self.filter_backends,
            self.default_added_filters,
            self.extra_filter_backends
        ))
        return backends

    def filter_queryset(self, queryset):
        for backend in self.get_filter_backends():
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset
