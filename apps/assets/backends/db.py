# -*- coding: utf-8 -*-
#
from django.db.models import F, CharField, Value
from django.db.models.functions import Concat

from ..models import AuthBook
from .base import BaseBackend


class AuthbookBackend(BaseBackend):
    model = AuthBook
    backend = 'authbook'
    base_score = 400

    def __init__(self):
        self.queryset = self.all()

    def get_queryset(self):
        return self.queryset

    def filter(self, assets=None, node=None, prefer_id=None, **kwargs):
        if assets:
            assets_id = self.make_assets_as_id(assets)
            self.queryset = self.queryset.filter(asset__in=assets_id)
        if node:
            self.queryset = self.queryset.filter(asset__node__id=node.id)
        kwargs = self.clean_kwargs(kwargs)
        if kwargs:
            self.queryset = self.queryset.filter(**kwargs)

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
