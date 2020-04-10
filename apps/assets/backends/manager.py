# -*- coding: utf-8 -*-
#
from itertools import chain, groupby
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from orgs.utils import current_org
from common.utils import get_logger, lazyproperty
from common.struct import QuerySetChain

from ..models import AssetUser, AuthBook
from .db import (
    AuthbookBackend, SystemUserBackend, AdminUserBackend,
    DynamicSystemUserBackend
)

logger = get_logger(__name__)


class NotSupportError(Exception):
    pass


class AssetUserQueryset:
    ObjectDoesNotExist = ObjectDoesNotExist
    MultipleObjectsReturned = MultipleObjectsReturned

    def __init__(self, backends=()):
        self.backends = backends
        self._distinct_queryset = None

    def backends_queryset(self):
        return [b.get_queryset() for b in self.backends]

    @lazyproperty
    def backends_counts(self):
        return [b.count() for b in self.backends]

    def filter(self, hostname=None, ip=None, username=None,
               assets=None, asset=None, node=None,
               id=None, prefer_id=None, prefer=None, id__in=None):
        if not assets and asset:
            assets = [asset]

        kwargs = dict(
            hostname=hostname, ip=ip, username=username,
            assets=assets, node=node, prefer=prefer, prefer_id=prefer_id,
            id__in=id__in, union_id=id,
        )
        logger.debug("Filter: {}".format(kwargs))
        backends = []
        for backend in self.backends:
            clone = backend.filter(**kwargs)
            backends.append(clone)
        return self._clone(backends)

    def _clone(self, backends=None):
        if backends is None:
            backends = self.backends
        return self.__class__(backends)

    def search(self, item):
        backends = []
        for backend in self.backends:
            new = backend.search(item)
            backends.append(new)
        return self._clone(backends)

    def distinct(self):
        logger.debug("Distinct asset user queryset")
        queryset_chain = chain(*(backend.get_queryset() for backend in self.backends))
        queryset_sorted = sorted(
            queryset_chain,
            key=lambda item: (item["asset_username"], item["score"]),
            reverse=True,
        )
        results = groupby(queryset_sorted, key=lambda item: item["asset_username"])
        final = [next(result[1]) for result in results]
        self._distinct_queryset = final
        return self

    def get(self, latest=False, **kwargs):
        queryset = self.filter(**kwargs)
        if latest:
            queryset = queryset.distinct()
        queryset = list(queryset)
        count = len(queryset)
        if count == 1:
            data = queryset[0]
            return data
        elif count > 1:
            msg = 'Should return 1 record, but get {}'.format(count)
            raise MultipleObjectsReturned(msg)
        else:
            msg = 'No record found(org is {})'.format(current_org.name)
            raise ObjectDoesNotExist(msg)

    def get_latest(self, **kwargs):
        return self.get(latest=True, **kwargs)

    @staticmethod
    def to_asset_user(data):
        obj = AssetUser()
        for k, v in data.items():
            setattr(obj, k, v)
        return obj

    @property
    def queryset(self):
        if self._distinct_queryset is not None:
            return self._distinct_queryset
        return QuerySetChain(self.backends_queryset())

    def count(self):
        if self._distinct_queryset is not None:
            return len(self._distinct_queryset)
        else:
            return sum(self.backends_counts)

    def __getitem__(self, ndx):
        return self.queryset.__getitem__(ndx)

    def __iter__(self):
        self._data = iter(self.queryset)
        return self

    def __next__(self):
        return self.to_asset_user(next(self._data))


class AssetUserManager:
    support_backends = (
        ('db', AuthbookBackend),
        ('system_user', SystemUserBackend),
        ('admin_user', AdminUserBackend),
        ('system_user_dynamic', DynamicSystemUserBackend),
    )

    def __init__(self):
        self.backends = [backend() for name, backend in self.support_backends]
        self._queryset = AssetUserQueryset(self.backends)

    def all(self):
        return self._queryset

    def delete(self, obj):
        name_backends_map = dict(self.support_backends)
        backend_name = obj.backend
        backend_cls = name_backends_map.get(backend_name)
        union_id = obj.union_id
        if backend_cls:
            backend_cls().delete(union_id)
        else:
            raise ObjectDoesNotExist("Not backend found")

    @staticmethod
    def create(**kwargs):
        # 使用create方法创建AuthBook对象，解决并发创建问题（添加锁机制）
        authbook = AuthBook.create(**kwargs)
        return authbook

    def __getattr__(self, item):
        return getattr(self._queryset, item)
