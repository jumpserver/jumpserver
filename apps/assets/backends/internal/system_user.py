# -*- coding: utf-8 -*-
#

from assets.models import SystemUser, Asset

from ..base import BaseBackend
from .utils import construct_authbook_object


class SystemUserBackend(BaseBackend):
    @classmethod
    def filter(cls, username=None, asset=None, **kwargs):
        system_users = SystemUser.objects.all()

        if username:
            system_users = system_users.filter(username=username)
        if asset:
            system_users = system_users.filter(assets=asset)

        instances = cls.construct_authbook_objects(system_users, asset)
        return instances

    @classmethod
    def _get_unique_assets(cls, username=None):
        if username is None:
            return Asset.objects.all()

        assets = set()
        system_users = SystemUser.objects.filter(username=username)
        for system_user in system_users:
            assets.update(system_user.assets.all())
        return assets

    @classmethod
    def _get_unique_username_list(cls, assets):
        username_set = SystemUser.objects.filter(assets__in=assets)\
            .values_list('username').distinct()
        return username_set

    @classmethod
    def _get_asset_latest_system_user(cls, asset, username):
        system_user = asset.systemuser_set.filter(username=username) \
            .order_by('-priority', '-date_updated').first()
        return system_user

    @classmethod
    def _construct_authbook_object(cls, asset, username):
        system_user = cls._get_asset_latest_system_user(asset, username)
        if not system_user:
            return None
        instance = construct_authbook_object(system_user, asset)
        return instance

    @classmethod
    def construct_authbook_objects(cls, assets, username_list):
        instances = []
        for asset in assets:
            for username in username_list:
                instance = cls._construct_authbook_object(asset, username)
                if not instance:
                    continue
                instances.append(instance)
        return instances

    @classmethod
    def create(cls, **kwargs):
        raise Exception("Not support create")


