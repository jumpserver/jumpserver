# -*- coding: utf-8 -*-
#

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from assets.models import SystemUser, Asset

from .. import meta
from .utils import construct_authbook_object


class SystemUserBackend:

    @classmethod
    def get(cls, username, asset):
        instances = cls.filter(username, asset)
        if len(instances) == 1:
            return instances[0]
        elif len(instances) == 0:
            msg = meta.EXCEPTION_MSG_NOT_EXIST.format(cls.__name__)
            raise ObjectDoesNotExist(msg)
        else:
            msg = meta.EXCEPTION_MSG_MULTIPLE.format(cls.__name__,
                                                     len(instances))
            raise MultipleObjectsReturned(msg)

    @classmethod
    def filter(cls, username=None, asset=None):
        if username and asset:
            assets = [asset]
            username_list = [username]

        elif username and not asset:
            assets = cls._get_unique_assets(username)
            username_list = [username]

        elif not username and asset:
            assets = [asset]
            username_list = cls._get_unique_username_list([asset])

        else:
            assets = cls._get_unique_assets()
            username_list = cls._get_unique_username_list(assets)

        instances = cls.get_authbook_objects(assets, username_list)
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
        username_set = set()
        for asset in assets:
            queryset = asset.systemuser_set.all().values('username')
            if not queryset:
                continue
            username_list = [q['username'] for q in queryset]
            username_set.update(username_list)
        return username_set

    @classmethod
    def _get_asset_latest_system_user(cls, asset, username):
        system_user = asset.systemuser_set.filter(username=username) \
            .order_by('-priority', '-date_updated').first()
        return system_user

    @classmethod
    def _get_authbook_object(cls, asset, username):
        system_user = cls._get_asset_latest_system_user(asset, username)
        if not system_user:
            return None
        instance = construct_authbook_object(system_user, asset)
        return instance

    @classmethod
    def get_authbook_objects(cls, assets, username_list):
        instances = []
        for asset in assets:
            for username in username_list:
                instance = cls._get_authbook_object(asset, username)
                if not instance:
                    continue
                instances.append(instance)
        return instances


