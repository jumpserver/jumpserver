# -*- coding: utf-8 -*-
#

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from assets.models import AdminUser, Asset
from .utils import construct_one_authbook_object


class AdminUserBackend:

    @classmethod
    def get(cls, username, asset):
        instances = cls.filter(username, asset)

        if len(instances) == 1:
            return instances[0]

        elif len(instances) == 0:
            msg = '{} Object matching query does not exist'.format(cls.__name__)
            raise ObjectDoesNotExist(msg)

        else:
            msg = '{} get() returned more than one object -- it returned {}!'\
                .format(cls.__name__, len(instances))
            raise MultipleObjectsReturned(msg)

    @classmethod
    def filter(cls, username=None, asset=None):
        if username and asset:
            if asset.admin_user.username != username:
                return []
            instance = construct_one_authbook_object(asset.admin_user, asset)
            return [instance]

        elif username and not asset:
            admin_users = AdminUser.objects.filter(username=username)
            instances = cls.construct_many_authbook_object(admin_users)
            return instances

        elif not username and asset:
            instance = construct_one_authbook_object(asset.admin_user, asset)
            return [instance]

        else:
            instances = []
            for tmp_asset in Asset.objects.all():
                instance = construct_one_authbook_object(tmp_asset.admin_user, tmp_asset)
                instances.append(instance)
            return instances

    @classmethod
    def construct_many_authbook_object(cls, admin_users):
        instances = []
        for admin_user in admin_users:
            for asset in admin_user.asset_set.all():
                instance = construct_one_authbook_object(admin_user, asset)
                instances.append(instance)
        return instances
