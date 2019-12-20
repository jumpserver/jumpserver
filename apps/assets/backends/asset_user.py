# -*- coding: utf-8 -*-
#
from collections import defaultdict
from itertools import islice, chain, groupby
from django.db.models import F, Value, CharField, IntegerField
from django.db.models.functions import Concat

from common.utils import timeit
from .base import BaseBackend
from ..models import SystemUser, Asset, AuthBook


class AssetUserBackend(BaseBackend):
    model = None
    backend = "AssetUser"

    @classmethod
    def filter_queryset_more(cls, queryset):
        return queryset

    @classmethod
    @timeit
    def filter(cls, username=None, assets=None, **kwargs):
        queryset = cls.model.objects.all()
        prefer_id = kwargs.get('prefer_id')
        if prefer_id:
            queryset = queryset.filter(id=prefer_id)
            instances = cls.construct_authbook_objects(queryset, assets)
            return instances
        if username:
            queryset = queryset.filter(username=username)
        if assets:
            queryset = queryset.filter(assets__in=assets).distinct()

        queryset = cls.filter_queryset_more(queryset)
        instances = cls.construct_authbook_objects(queryset, assets)
        return instances

    @classmethod
    def construct_authbook_objects(cls, asset_users, assets):
        instances = []
        assets_user_assets_map = defaultdict(set)
        if isinstance(asset_users, list):
            assets_user_assets_map = {
                asset_user.id: asset_user.assets.values_list('id', flat=True)
                for asset_user in asset_users
            }
        else:
            assets_user_assets = asset_users.values_list('id', 'assets')
            for i, asset_id in assets_user_assets:
                assets_user_assets_map[i].add(asset_id)

        for asset_user in asset_users:
            if not assets:
                related_assets = asset_user.assets.all()
            else:
                assets_map = {a.id: a for a in assets}
                related_assets = [
                    assets_map.get(i) for i in assets_user_assets_map.get(asset_user.id) if i in assets_map
                ]
            for asset in related_assets:
                instance = asset_user.construct_to_authbook(asset)
                instance.backend = cls.backend
                instances.append(instance)
        return instances

from django.db.models import QuerySet


def to_asset_user_queryset(qs):
    values = qs.values(
        'hostname', 'ip', "asset_id",
        'username', 'password', 'private_key', 'public_key',
        'score', 'version',
        "asset_username", "union_id",
        'date_created', 'date_updated',
        'org_id', 'backend',
    )
    return values


class BaseManager:
    pass
    # def __init__(self, qs=None):
    #     if qs is None:
    #         qs = qs
    #     self.qs = qs
    #
    # def to_asset_user_queryset(self):
    #     values = self.qs.values(
    #         'id', 'username', 'password', 'private_key', 'public_key',
    #         'score', 'hostname', 'ip', 'date_created', 'date_updated',
    #         'org_id', 'backend', "asset_id", "union_id"
    #     )
    #     return values
    #
    # def __getattr__(self, item):
    #     return getattr(self.qs, item)


class AssetSystemUserManager(BaseManager):
    model = SystemUser.assets.through
    backend = 'system_user'
    base_score = 0

    def query_all(self):
        kwargs = dict(
            hostname=F("asset__hostname"),
            ip=F("asset__ip"),
            username=F("systemuser__username"),
            password=F("systemuser__password"),
            private_key=F("systemuser__private_key"),
            public_key=F("systemuser__public_key"),
            score=F("systemuser__priority") + self.base_score,
            version=Value(0, IntegerField()),
            date_created=F("systemuser__date_created"),
            date_updated=F("systemuser__date_updated"),
            asset_username=Concat(F("asset__id"), Value("_"), F("systemuser__username"), output_field=CharField()),
            union_id=Concat(F("systemuser_id"), Value("_"), F("asset_id"), output_field=CharField()),
            org_id=F("asset__org_id"),
            backend=Value(self.backend, CharField())
        )

        qs = self.model.objects.all().annotate(**kwargs)
        return to_asset_user_queryset(qs)


class AssetAdminUserManager(BaseManager):
    model = Asset
    backend = 'admin_user'
    base_score = 200

    def query_all(self):
        qs = self.model.objects.all().annotate(
            asset_id=F("id"),
            username=F("admin_user__username"),
            password=F("admin_user__password"),
            private_key=F("admin_user__private_key"),
            public_key=F("admin_user__public_key"),
            score=Value(self.base_score, IntegerField()),
            version=Value(0, IntegerField()),
            date_updated=F("admin_user__date_updated"),
            asset_username=Concat(F("id"), Value("_"), F("admin_user__username"), output_field=CharField()),
            union_id=Concat(F("admin_user_id"), Value("_"), F("id"), output_field=CharField()),
            backend=Value(self.backend, CharField()),
        )
        return to_asset_user_queryset(qs)


class AuthbookManager(BaseManager):
    model = AuthBook
    backend = 'authbook'
    base_score = 400

    def query_all(self):
        qs = self.model.objects.all().annotate(
            hostname=F("asset__hostname"),
            ip=F("asset__ip"),
            score=F('version') + self.base_score,
            asset_username=Concat(F("asset__id"), Value("_"), F("username"), output_field=CharField()),
            union_id=Concat(F("id"), Value("_"), F("asset_id"), output_field=CharField()),
            backend=Value(self.backend, CharField()),
        )
        return to_asset_user_queryset(qs)


class QuerySetChain:
    def __init__(self, *subquerysets):
        self.querysets = subquerysets
        self.queryset = None

    def distinct(self):
        queryset_chain = chain(*self.querysets)
        queryset_sorted = sorted(
            queryset_chain,
            key=lambda item: (item["asset_username"], item["score"]),
            reverse=True,
        )
        results = groupby(queryset_sorted, key=lambda item: item["asset_username"])
        final = (next(result[1]) for result in results)
        return final

    def filter(self, **kwargs):
        self.querysets = [qs.filter(**kwargs) for qs in self.querysets]
        self.queryset = None

    def count(self):
        return sum(qs.count() for qs in self.querysets)

    def _clone(self):
        return self.__class__(*self.querysets)

    def _all(self):
        return chain(*self.querysets)

    def __getitem__(self, ndx):
        if type(ndx) is slice:
            return list(islice(self._all(), ndx.start, ndx.stop, ndx.step or 1))
        else:
            return next(islice(self._all(), ndx, ndx+1))
