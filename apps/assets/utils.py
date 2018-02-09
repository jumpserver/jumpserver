# ~*~ coding: utf-8 ~*~
#
from collections import defaultdict
from functools import reduce
import operator

from django.db.models import Q

from common.utils import get_object_or_none
from .models import Asset, SystemUser, Label


def get_assets_by_id_list(id_list):
    return Asset.objects.filter(id__in=id_list)


def get_assets_by_hostname_list(hostname_list):
    return Asset.objects.filter(hostname__in=hostname_list)


def get_system_user_by_name(name):
    system_user = get_object_or_none(SystemUser, name=name)
    return system_user


class LabelFilter:
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        query_keys = self.request.query_params.keys()
        all_label_keys = Label.objects.values_list('name', flat=True)
        valid_keys = set(all_label_keys) & set(query_keys)
        labels_query = {}
        for key in valid_keys:
            labels_query[key] = self.request.query_params.get(key)

        conditions = []
        for k, v in labels_query.items():
            query = {'labels__name': k, 'labels__value': v}
            conditions.append(query)

        if conditions:
            for kwargs in conditions:
                queryset = queryset.filter(**kwargs)
        return queryset




