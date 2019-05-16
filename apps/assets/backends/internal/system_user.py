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
    def _distinct_system_users_by_username(cls, system_users):
        system_users = sorted(
            system_users,
            key=lambda su: (su.username, su.priority, su.date_updated),
            reverse=True,
        )
        results = itertools.groupby(system_users, key=lambda su: su.username)
        system_users = [next(result[1]) for result in results]
        return system_users

    @classmethod
    def _filter_system_users_by_username(cls, system_users, username):
        _system_users = cls._distinct_system_users_by_username(system_users)
        if username is not None:
            _system_users = [su for su in _system_users if username == su.username]
        return _system_users

    @classmethod
    def _construct_authbook_objects(cls, system_users, asset):
        instances = []
        for system_user in system_users:
            instance = construct_authbook_object(system_user, asset)
            instances.append(instance)
        return instances

    @classmethod
    def _get_assets_with_system_users(cls, asset=None):
        """
        { 'asset': set(<SystemUser>, <SystemUser>, ...) }
        """
        if not asset:
            _assets = Asset.objects.all().prefetch_related('systemuser_set')
        else:
            _assets = [asset]

        assets = {asset: set(asset.systemuser_set.all()) for asset in _assets}
        return assets

    @classmethod
    def construct_authbook_objects(cls, username, asset):
        """
        :return: [<AuthBook>, <AuthBook>, ...]
        """
        instances = []
        assets = cls._get_assets_with_system_users(asset)
        for _asset, _system_users in assets.items():
            _system_users = cls._filter_system_users_by_username(_system_users, username)
            _instances = cls._construct_authbook_objects(_system_users, _asset)
            instances.extend(_instances)
        return instances

    @classmethod
    def create(cls, **kwargs):
        raise Exception("Not support create")


