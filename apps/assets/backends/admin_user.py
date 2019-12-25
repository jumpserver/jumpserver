# -*- coding: utf-8 -*-
#
from django.db.models import F, Value, IntegerField, CharField
from django.db.models.functions import Concat

from ..models import Asset
from .base import BaseBackend


class AdminUserBackend(BaseBackend):
    model = Asset
    backend = 'admin_user'
    base_score = 200

    def __init__(self):
        self.queryset = self.all()

    def get_queryset(self):
        return self.queryset

    def filter(self, assets=None, node=None, prefer_id=None, **kwargs):
        if prefer_id:
            self.queryset = self.queryset.filter(admin_user__id=prefer_id)
            return
        if assets:
            assets_id = self.make_assets_as_id(assets)
            self.queryset = self.queryset.filter(id__in=assets_id)
        if node:
            self.queryset = self.queryset.filter(node__key=node.key)
        kwargs = self.clean_kwargs(kwargs)
        if kwargs:
            self.queryset = self.queryset.filter(**kwargs)

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
