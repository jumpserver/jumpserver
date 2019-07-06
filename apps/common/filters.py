# -*- coding: utf-8 -*-
#
from rest_framework import filters
from rest_framework.fields import DateTimeField
from rest_framework.serializers import ValidationError
import logging

__all__ = ["DatetimeRangeFilter"]


class DatetimeRangeFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if not hasattr(view, 'date_range_filter_fields'):
            return queryset
        try:
            fields = dict(view.date_range_filter_fields)
        except ValueError:
            msg = "View {} datetime_filter_fields set is error".format(view.name)
            logging.error(msg)
            return queryset
        kwargs = {}
        for attr, date_range_keyword in fields.items():
            if len(date_range_keyword) != 2:
                continue
            for i, v in enumerate(date_range_keyword):
                value = request.query_params.get(v)
                if not value:
                    continue
                try:
                    field = DateTimeField()
                    value = field.to_internal_value(value)
                    if i == 0:
                        lookup = "__gte"
                    else:
                        lookup = "__lte"
                    kwargs[attr+lookup] = value
                except ValidationError as e:
                    print(e)
                    continue
        if kwargs:
            queryset = queryset.filter(**kwargs)
        return queryset
