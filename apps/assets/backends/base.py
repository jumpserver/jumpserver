# -*- coding: utf-8 -*-
#
from abc import abstractmethod

from ..models import Asset


class BaseBackend:
    @abstractmethod
    def all(self):
        pass

    @abstractmethod
    def filter(self, username=None, hostname=None, ip=None, assets=None,
               node=None, prefer_id=None, **kwargs):
        pass

    @abstractmethod
    def search(self, item):
        pass

    @abstractmethod
    def get_queryset(self):
        pass

    @abstractmethod
    def delete(self, union_id):
        pass

    @staticmethod
    def qs_to_values(qs):
        values = qs.values(
            'hostname', 'ip', "asset_id",
            'username', 'password', 'private_key', 'public_key',
            'score', 'version',
            "asset_username", "union_id",
            'date_created', 'date_updated',
            'org_id', 'backend',
        )
        return values

    @staticmethod
    def make_assets_as_id(assets):
        if not assets:
            return []
        if isinstance(assets[0], Asset):
            assets = [a.id for a in assets]
        return assets
