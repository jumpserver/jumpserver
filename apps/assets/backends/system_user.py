# -*- coding: utf-8 -*-
#

from django.db.models import F, Value, IntegerField, CharField
from django.db.models.functions import Concat

from assets.models import SystemUser
from .base import BaseBackend


class SystemUserBackend(BaseBackend):
    model = SystemUser.assets.through
    backend = 'SystemUser'
    base_score = 0

    def __init__(self):
        self.queryset = self.all()

    def filter(self, assets=None, node=None, prefer_id=None, **kwargs):
        if prefer_id:
            self.queryset = self.queryset.filter(systemuser__id=prefer_id)
            return
        if assets:
            assets_id = self.make_assets_as_id(assets)
            self.queryset = self.queryset.filter(asset__id__in=assets_id)
        if node:
            self.queryset = self.queryset.filter(asset__nodes__id=node.id)
        kwargs = self.clean_kwargs(kwargs)
        if kwargs:
            self.queryset = self.queryset.filter(**kwargs)

    def get_queryset(self):
        return self.queryset

    def all(self):
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
        qs = self.model.objects.all().annotate(**kwargs)
        qs = self.qs_to_values(qs)
        return qs
