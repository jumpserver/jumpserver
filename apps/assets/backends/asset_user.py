# -*- coding: utf-8 -*-
#
from collections import defaultdict
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
