# -*- coding: utf-8 -*-
#

import itertools

from assets.models import Asset

from ..base import BaseBackend
from .utils import construct_authbook_object


class SystemUserBackend(BaseBackend):

    @classmethod
    def filter(cls, username=None, asset=None, **kwargs):
        instances = cls.construct_authbook_objects(username, asset)
        return instances

    @classmethod
    def _construct_authbook_objects(cls, system_users, asset):
        instances = []
        for system_user in system_users:
            instance = construct_authbook_object(system_user, asset)
            instances.append(instance)
        return instances

    @classmethod
    def _distinct_system_users_by_username(cls, system_users):
        system_users = system_users.order_by('username', '-priority', '-date_updated')
        results = itertools.groupby(system_users, key=lambda su: su.username)
        system_users = [next(result[1]) for result in results]
        return system_users

    @classmethod
    def _get_assets_with_system_users(cls, username=None, asset=None):
        """
        { 'assets': <QuerySet [<SystemUser>, <SystemUser>, ...]> }
        """
        if not asset:
            _assets = Asset.objects.all().prefetch_related('systemuser_set')
        else:
            _assets = [asset]

        if not username:
            assets = {asset: asset.systemuser_set.all() for asset in _assets}
        else:
            assets = {asset: asset.systemuser_set.filter(username=username)
                      for asset in _assets}
        return assets

    @classmethod
    def construct_authbook_objects(cls, username, asset):
        """
        :return: [<AuthBook>, <AuthBook>, ...]
        """
        instances = []
        assets = cls._get_assets_with_system_users(username, asset)
        for asset, system_users in assets.items():
            _system_users = cls._distinct_system_users_by_username(system_users)
            _instances = cls._construct_authbook_objects(_system_users, asset)
            instances.extend(_instances)
        return instances

    @classmethod
    def create(cls, **kwargs):
        raise Exception("Not support create")


