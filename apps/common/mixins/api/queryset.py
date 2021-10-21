# -*- coding: utf-8 -*-
#

__all__ = ['QuerySetMixin']


class QuerySetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        serializer_class = self.get_serializer_class()

        if serializer_class and hasattr(serializer_class, 'setup_eager_loading'):
            queryset = serializer_class.setup_eager_loading(queryset)
        return queryset
