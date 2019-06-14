# -*- coding: utf-8 -*-
#

import itertools

from assets.models import SystemUser
from .asset_user import AssetUserBackend


class SystemUserBackend(AssetUserBackend):
    model = SystemUser
    backend = 'SystemUser'

    @classmethod
    def filter_queryset_more(cls, queryset):
        queryset = cls._distinct_system_users_by_username(queryset)
        return queryset

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


