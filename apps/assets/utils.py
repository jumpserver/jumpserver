# ~*~ coding: utf-8 ~*~
#
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache
from django.utils import timezone

from common.utils import get_object_or_none
from .models import Asset, SystemUser, Label


def get_assets_by_id_list(id_list):
    return Asset.objects.filter(id__in=id_list).filter(is_active=True)


def get_system_users_by_id_list(id_list):
    return SystemUser.objects.filter(id__in=id_list)


def get_system_user_by_name(name):
    system_user = get_object_or_none(SystemUser, name=name)
    return system_user


def get_system_user_by_id(id):
    system_user = get_object_or_none(SystemUser, id=id)
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


class Connectivity:
    UNREACHABLE, REACHABLE, UNKNOWN = range(0, 3)
    CONNECTIVITY_CHOICES = (
        (UNREACHABLE, _("Unreachable")),
        (REACHABLE, _('Reachable')),
        (UNKNOWN, _("Unknown")),
    )

    value = UNKNOWN
    datetime = timezone.now()

    def __init__(self, value, datetime):
        self.value = value
        self.datetime = datetime

    def display(self):
        return dict(self.__class__.CONNECTIVITY_CHOICES).get(self.value)

    def is_reachable(self):
        return self.value == self.REACHABLE

    def is_unreachable(self):
        return self.value == self.UNREACHABLE

    def is_unknown(self):
        return self.value == self.UNKNOWN

    @classmethod
    def unreachable(cls):
        return cls(cls.UNREACHABLE, timezone.now())

    @classmethod
    def reachable(cls):
        return cls(cls.REACHABLE, timezone.now())

    @classmethod
    def unknown(cls):
        return cls(cls.UNKNOWN, timezone.now())

    @classmethod
    def set(cls, key, value, ttl=0):
        cache.set(key, value, ttl)

    @classmethod
    def get(cls, key):
        return cache.get(key, cls.UNKNOWN)

    @classmethod
    def set_unreachable(cls, key, ttl=0):
        cls.set(key, cls.unreachable(), ttl)

    @classmethod
    def set_reachable(cls, key, ttl=0):
        cls.set(key, cls.reachable(), ttl)

    def __eq__(self, other):
        return self.value == other.value
