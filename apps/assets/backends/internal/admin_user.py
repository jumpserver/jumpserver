# -*- coding: utf-8 -*-
#

from assets.models import Asset

from ..base import BaseBackend
from .utils import construct_authbook_object


class AdminUserBackend(BaseBackend):

    @classmethod
    def filter(cls, username=None, asset=None, **kwargs):
        instances = cls.construct_authbook_objects(username, asset)
        return instances

    @classmethod
    def _get_assets(cls, username, asset):
        if not asset:
            assets = Asset.objects.all().prefetch_related('admin_user')
        else:
            assets = [asset]

        if username:
            assets = [
                _asset for _asset in assets
                if _asset.admin_user.username == username
            ]
        return assets

    @classmethod
    def construct_authbook_objects(cls, username, asset):
        instances = []
        assets = cls._get_assets(username, asset)
        for asset in assets:
            instance = construct_authbook_object(asset.admin_user, asset)
            instances.append(instance)
        return instances

    @classmethod
    def create(cls, **kwargs):
        raise cls.NotSupportError("Not support create")
