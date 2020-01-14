# -*- coding: utf-8 -*-
#
from functools import reduce
from django.db.models import F, CharField, Value, IntegerField, Q, Count
from django.db.models.functions import Concat

from common.utils import get_object_or_none
from orgs.utils import current_org
from ..models import AuthBook, SystemUser, Asset, AdminUser
from .base import BaseBackend


class DBBackend(BaseBackend):
    def __init__(self, queryset=None):
        if queryset is None:
            queryset = self.all()
        self.queryset = queryset

    def _clone(self):
        return self.__class__(self.queryset)

    def all(self):
        return AuthBook.objects.none()

    def count(self):
        return self.queryset.count()

    def get_queryset(self):
        return self.queryset

    def filter(self, assets=None, node=None, prefer=None, prefer_id=None,
               union_id=None, id__in=None, **kwargs):
        clone = self._clone()
        clone._filter_union_id(union_id)
        clone._filter_prefer(prefer, prefer_id)
        clone._filter_node(node)
        clone._filter_assets(assets)
        clone._filter_other(kwargs)
        clone._filter_id_in(id__in)
        return clone

    def _filter_union_id(self, union_id):
        if union_id:
            self.queryset = self.queryset.filter(union_id=union_id)

    def _filter_assets(self, assets):
        assets_id = self.make_assets_as_id(assets)
        if assets_id:
            self.queryset = self.queryset.filter(asset_id__in=assets_id)

    def _filter_node(self, node):
        pass

    def _filter_id_in(self, ids):
        if ids and isinstance(ids, list):
            self.queryset = self.queryset.filter(union_id__in=ids)

    def count(self):
        return self.queryset.count()

    @staticmethod
    def clean_kwargs(kwargs):
        return {k: v for k, v in kwargs.items() if v}

    def _filter_other(self, kwargs):
        kwargs = self.clean_kwargs(kwargs)
        if kwargs:
            self.queryset = self.queryset.filter(**kwargs)

    def _filter_prefer(self, prefer, prefer_id):
        pass

    def search(self, item):
        qs = []
        for i in ['hostname', 'ip', 'username']:
            kwargs = {i + '__startswith': item}
            qs.append(Q(**kwargs))
        q = reduce(lambda x, y: x | y, qs)
        clone = self._clone()
        clone.queryset = clone.queryset.filter(q).distinct()
        return clone


class SystemUserBackend(DBBackend):
    model = SystemUser.assets.through
    backend = 'system_user'
    base_score = 0

    def _filter_prefer(self, prefer, prefer_id):
        if prefer and prefer != self.backend:
            self.queryset = self.queryset.none()

        if prefer_id:
            self.queryset = self.queryset.filter(systemuser__id=prefer_id)

    def _filter_node(self, node):
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
        if current_org.org_id() is not None:
            filters['org_id'] = current_org.org_id()
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

    def _filter_prefer(self, prefer, prefer_id):
        if prefer and prefer != self.backend:
            self.queryset = self.queryset.none()
        if prefer_id:
            self.queryset = self.queryset.filter(admin_user__id=prefer_id)

    def _filter_node(self, node):
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

    def _filter_node(self, node):
        if node:
            self.queryset = self.queryset.filter(asset__nodes__id=node.id)

    def _filter_prefer(self, prefer, prefer_id):
        if not prefer or not prefer_id:
            return
        if prefer.lower() in ("admin_user", "adminuser"):
            model = AdminUser
        elif prefer.lower() in ("system_user", "systemuser"):
            model = SystemUser
        else:
            self.queryset = self.queryset.none()
            return
        obj = get_object_or_none(model, pk=prefer_id)
        if obj is None:
            self.queryset = self.queryset.none()
            return
        username = obj.get_username()
        if isinstance(username, str):
            self.queryset = self.queryset.filter(username=username)
        # dynamic system user return more username
        else:
            self.queryset = self.queryset.filter(username__in=username)

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
