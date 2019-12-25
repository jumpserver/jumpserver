# -*- coding: utf-8 -*-
#
from itertools import islice, chain, groupby
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from ..models import AssetUser

from .db import AuthbookBackend
from .system_user import SystemUserBackend
from .admin_user import AdminUserBackend


class NotSupportError(Exception):
    pass


class AssetUserQueryset:
    def __init__(self, backends=()):
        self.backends = backends
        self._queryset = None

    def filter(self, hostname=None, ip=None, username=None, assets=None,
               asset=None, node=None, prefer_id=None):
        if not assets and asset:
            assets = [asset]
        kwargs = dict(
            hostname=hostname, ip=ip, username=username,
            assets=assets, node=node, prefer_id=prefer_id,
        )
        print("Filter: {}".format(kwargs))
        for backend in self.backends:
            backend.filter(**kwargs)
        return self

    def distinct(self):
        print("dictinct")
        queryset_chain = chain(*(backend.get_queryset() for backend in self.backends))
        print("Chain it")
        queryset_sorted = sorted(
            queryset_chain,
            key=lambda item: (item["asset_username"], item["score"]),
            reverse=True,
        )
        print("Sorted")
        results = groupby(queryset_sorted, key=lambda item: item["asset_username"])
        print("groupby")
        final = [next(result[1]) for result in results]
        self._queryset = final

    def get(self, **kwargs):
        self.filter(**kwargs)
        count = self.count()
        if count == 1:
            return self.queryset[0]
        elif count > 1:
            msg = '{} get'.format(count)
            raise MultipleObjectsReturned(msg)
        else:
            raise ObjectDoesNotExist()

    def get_object(self, **kwargs):
        data = self.get(**kwargs)
        obj = AssetUser()
        for k, v in data.items():
            setattr(obj, k, v)
        return obj

    @property
    def queryset(self):
        if self._queryset is None:
            self.distinct()
        return self._queryset

    def count(self):
        return len(self.queryset)

    def __getitem__(self, ndx):
        if type(ndx) is slice:
            return list(islice(self.queryset, ndx.start, ndx.stop, ndx.step or 1))
        else:
            return self.queryset[ndx]


class AssetUserManager:
    backends = (
        ('db', AuthbookBackend),
        ('system_user', SystemUserBackend),
        ('admin_user', AdminUserBackend),
    )

    def __init__(self):
        self.backends = [backend() for name, backend in self.backends]
        self._queryset = AssetUserQueryset(self.backends)

    def all(self):
        return self._queryset

    def __getattr__(self, item):
        return getattr(self._queryset, item)
