# -*- coding: utf-8 -*-
#
from itertools import islice, chain, groupby
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from common.utils import get_logger

from ..models import AssetUser
from .db import AuthbookBackend, SystemUserBackend, AdminUserBackend

logger = get_logger(__name__)


class NotSupportError(Exception):
    pass


class AssetUserQueryset:
    def __init__(self, backends=()):
        self.backends = backends
        self._queryset = None

    def filter(self, hostname=None, ip=None, username=None, assets=None,
               asset=None, node=None, prefer_id=None, **kwargs):
        if not assets and asset:
            assets = [asset]
        kwargs.update(dict(
            hostname=hostname, ip=ip, username=username,
            assets=assets, node=node, prefer_id=prefer_id,
        ))
        logger.debug("Filter: {}".format(kwargs))
        for backend in self.backends:
            backend.filter(**kwargs)
        return self

    def search(self, item):
        for backend in self.backends:
            backend.search(item)
        return self

    def distinct(self):
        authbook_asset_username = set(
            self.backends[0].value_list('asset_username', flat=True)
        )
        for backend in self.backends[1:]:
            backend.exclude(authbook_asset_username)

        # logger.debug("Chain it")
        # queryset_chain = chain(*(backend.get_queryset() for backend in self.backends))
        # logger.debug("Sort it")
        # queryset_sorted = sorted(
        #     queryset_chain,
        #     key=lambda item: (item["asset_username"], item["score"]),
        #     reverse=True,
        # )
        # logger.debug("Group by it")
        # results = groupby(queryset_sorted, key=lambda item: item["asset_username"])
        # logger.debug("Get the first")
        # final = [next(result[1]) for result in results]
        # logger.debug("End")
        # self._queryset = final

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
