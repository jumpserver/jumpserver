# -*- coding: utf-8 -*-
#
from functools import reduce
from django.db.models import F, CharField, Value, IntegerField, Q, Count
from django.db.models.functions import Concat

from orgs.utils import current_org
from ..models import AuthBook, SystemUser, Asset
from .base import BaseBackend


class DBBackend(BaseBackend):
    def __init__(self):
        self.queryset = self.all()

    def all(self):
        return AuthBook.objects.none()

    def get_queryset(self):
        return self.queryset

    def filter(self, assets=None, node=None, prefer=None, prefer_id=None,
               id__in=None, **kwargs):
        self.filter_prefer(prefer, prefer_id)
        self.filter_node(node)
        self.filter_assets(assets)
        self.filter_other(kwargs)
        self.filter_id_in(id__in)

    def filter_assets(self, assets):
        assets_id = self.make_assets_as_id(assets)
        if assets_id:
            self.queryset = self.queryset.filter(asset_id__in=assets_id)

    def filter_node(self, node):
        pass

    def filter_id_in(self, ids):
        if ids and isinstance(ids, list):
            self.queryset = self.queryset.filter(union_id__in=ids)

    def count(self):
        return self.queryset.count()

    @staticmethod
    def clean_kwargs(kwargs):
        return {k: v for k, v in kwargs.items() if v}

    def filter_other(self, kwargs):
        kwargs = self.clean_kwargs(kwargs)
        if kwargs:
            self.queryset = self.queryset.filter(**kwargs)

    def filter_prefer(self, prefer, prefer_id):
        pass

    def search(self, item):
        qs = []
        for i in ['hostname', 'ip', 'username']:
            kwargs = {i + '__startswith': item}
            qs.append(Q(**kwargs))
        q = reduce(lambda x, y: x | y, qs)
        self.queryset = self.queryset.filter(q).distinct()


class SystemUserBackend(DBBackend):
    model = SystemUser.assets.through
    backend = 'system_user'
    base_score = 0

    def filter_prefer(self, prefer, prefer_id):
        if prefer and prefer != self.backend:
            self.queryset = self.queryset.none()

        if prefer_id:
            self.queryset = self.queryset.filter(systemuser__id=prefer_id)

    def filter_node(self, node):
        if node:
            self.queryset = self.queryset.filter(asset__nodes__id=node.id)

    def get_annotate(self):
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
            asset_username=Concat(F("asset__id"), Value("_"),
                                  F("systemuser__username"),
                                  output_field=CharField()),
            union_id=Concat(F("systemuser_id"), Value("_"), F("asset_id"),
                            output_field=CharField()),
            org_id=F("asset__org_id"),
            backend=Value(self.backend, CharField())
        )
        return kwargs

    def get_filter(self):
        return dict(
            systemuser__username_same_with_user=False,
        )

    def all(self):
        kwargs = self.get_annotate()
        filters = self.get_filter()
        qs = self.model.objects.all().annotate(**kwargs)
        org_id = ''
        if current_org.is_real():
            org_id = current_org.id
        filters['org_id'] = org_id
        qs = qs.filter(**filters)
        qs = self.qs_to_values(qs)
        return qs


class DynamicSystemUserBackend(SystemUserBackend):
    backend = 'system_user'

    def get_annotate(self):
        kwargs = super().get_annotate()
        kwargs.update(dict(
            username=F("systemuser__users__username"),
            asset_username=Concat(
                F("asset__id"), Value("_"),
                F("systemuser__users__username"),
                output_field=CharField()
            ),
            union_id=Concat(
                F("systemuser_id"), Value("_"), F("asset_id"),
                Value("_"), F("systemuser__users__id"),
                output_field=CharField()
            ),
            users_count=Count('systemuser__users'),
        ))
        return kwargs

    def get_filter(self):
        return dict(
            users_count__gt=0,
            systemuser__username_same_with_user=True
        )


class AdminUserBackend(DBBackend):
    model = Asset
    backend = 'admin_user'
    base_score = 200

    def filter_prefer(self, prefer, prefer_id):
        if prefer and prefer != self.backend:
            self.queryset = self.queryset.none()
        if prefer_id:
            self.queryset = self.queryset.filter(admin_user__id=prefer_id)

    def filter_node(self, node):
        if node:
            self.queryset = self.queryset.filter(nodes__id=node.id)

    def all(self):
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
        qs = self.qs_to_values(qs)
        return qs


class AuthbookBackend(DBBackend):
    model = AuthBook
    backend = 'db'
    base_score = 400

    def filter_node(self, node):
        if node:
            self.queryset = self.queryset.filter(asset__nodes__id=node.id)

    def all(self):
        qs = self.model.objects.all().annotate(
            hostname=F("asset__hostname"),
            ip=F("asset__ip"),
            score=F('version') + self.base_score,
            asset_username=Concat(F("asset__id"), Value("_"), F("username"), output_field=CharField()),
            union_id=Concat(F("id"), Value("_"), F("asset_id"), output_field=CharField()),
            backend=Value(self.backend, CharField()),
        )
        qs = self.qs_to_values(qs)
        return qs
