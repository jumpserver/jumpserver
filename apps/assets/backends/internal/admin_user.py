# -*- coding: utf-8 -*-
#

from assets.models import AdminUser, Asset

from ..base import BaseBackend
from .utils import construct_authbook_object


class AdminUserBackend(BaseBackend):
    @classmethod
    def filter(cls, username=None, asset=None, **kwargs):
        if username and asset:
            if username != asset.admin_user.username:
                return []
            assets = [asset]

        elif username and not asset:
            assets = cls._get_unique_assets(username)

        elif not username and asset:
            assets = [asset]

        else:
            assets = cls._get_unique_assets()

        instances = cls.construct_authbook_objects(assets)
        return instances

    @classmethod
    def _get_unique_assets(cls, username=None):
        if username is None:
            return Asset.objects.all()

        admin_users = AdminUser.objects.filter(username=username)
        assets = Asset.objects.filter(admin_user__in=admin_users).disinct()
        return assets

    @classmethod
    def construct_authbook_objects(cls, assets):
        instances = []
        for asset in assets:
            instance = construct_authbook_object(asset.admin_user, asset)
            instances.append(instance)
        return instances

    @classmethod
    def create(cls, **kwargs):
        raise cls.NotSupportError("Not support create")
