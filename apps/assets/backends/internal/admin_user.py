# -*- coding: utf-8 -*-
#

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from assets.models import AdminUser, Asset

from .. import meta
from .utils import construct_authbook_object


class AdminUserBackend:

    @classmethod
    def get(cls, username, asset):
        instances = cls.filter(username, asset)
        if len(instances) == 1:
            return instances[0]
        elif len(instances) == 0:
            msg = meta.EXCEPTION_MSG_NOT_EXIST.format(cls.__name__)
            raise ObjectDoesNotExist(msg)
        else:
            msg = meta.EXCEPTION_MSG_MULTIPLE.format(cls.__name__, len(instances))
            raise MultipleObjectsReturned(msg)

    @classmethod
    def filter(cls, username=None, asset=None):
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

        instances = cls.get_authbook_objects(assets)
        return instances

    @classmethod
    def _get_unique_assets(cls, username=None):
        if username is None:
            return Asset.objects.all()

        assets = set()
        admin_users = AdminUser.objects.filter(username=username)
        for admin_user in admin_users:
            queryset = admin_user.asset_set.all()
            assets.update(queryset)
        return assets

    @classmethod
    def _get_authbook_object(cls, asset):
        instance = construct_authbook_object(asset.admin_user, asset)
        return instance

    @classmethod
    def get_authbook_objects(cls, assets):
        instances = []
        for asset in assets:
            instance = cls._get_authbook_object(asset)
            instances.append(instance)
        return instances
