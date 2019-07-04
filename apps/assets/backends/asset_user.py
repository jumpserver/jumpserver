# -*- coding: utf-8 -*-
#
from .base import BaseBackend


class AssetUserBackend(BaseBackend):
    model = None
    backend = "AssetUser"

    @classmethod
    def filter_queryset_more(cls, queryset):
        return queryset

    @classmethod
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
        for asset_user in asset_users:
            if not assets:
                assets = asset_user.assets.all()
            for asset in assets:
                instance = asset_user.construct_to_authbook(asset)
                instance.backend = cls.backend
                instances.append(instance)
        return instances
