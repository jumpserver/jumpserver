# -*- coding: utf-8 -*-
#

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from assets.models import SystemUser

from .utils import construct_one_authbook_object


class SystemUserBackend:

    @classmethod
    def get(cls, username, asset):
        instances = cls.filter(username, asset)
        if len(instances) == 1:
            return instances[0]

        elif len(instances) == 0:
            msg = '{} Object matching query does not exist'.format(cls.__name__)
            raise ObjectDoesNotExist(msg)

        else:
            msg = '{} get() returned more than one object -- it returned {}!' \
                .format(cls.__name__, len(instances))
            raise MultipleObjectsReturned(msg)

    @classmethod
    def filter(cls, username=None, asset=None):
        if username and asset:
            system_user = asset.systemuser_set.filter(username=username)\
                .order_by('-priority', '-date_updated').first()
            if not system_user:
                return []
            instance = construct_one_authbook_object(system_user, asset)
            return [instance]

        if username and not asset:
            assets = set()
            system_users = SystemUser.objects.filter(username=username)
            for system_user in system_users:
                assets.update(system_user.assets.all())

            instances = []
            for tmp_asset in assets:
                system_user = tmp_asset.systemuser_set.filter(username=username)\
                    .order_by('-priority', '-date_updated').first()
                if not system_user:
                    return []
                instance = construct_one_authbook_object(system_user, tmp_asset)
                instances.append(instance)

            return instances

        if not username and asset:
            system_users = []
            queryset = asset.systemuser_set.all().values('username')
            username_list = set([q['username'] for q in queryset])
            for username in username_list:
                system_user = SystemUser.objects.filter(username=username)\
                    .order_by('-priority', '-date_updated').first()
                system_users.append(system_user)

            instances = []
            for system_user in system_users:
                instance = construct_one_authbook_object(system_user, asset)
                instances.append(instance)
            return instances

        else:
            return []
