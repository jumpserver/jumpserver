# -*- coding: utf-8 -*-
#

from ..models import AuthBook
from .base import BaseBackend


class AuthBookBackend(BaseBackend):
    @classmethod
    def filter(cls, username=None, assets=None, latest=True, **kwargs):
        queryset = AuthBook.objects.all()
        if username is not None:
            queryset = queryset.filter(username=username)
        if assets:
            queryset = queryset.filter(asset__in=assets)
        if latest:
            queryset = queryset.latest_version()
        return queryset

    @classmethod
    def create(cls, **kwargs):
        auth_info = {
            'password': kwargs.pop('password', ''),
            'public_key': kwargs.pop('public_key', ''),
            'private_key': kwargs.pop('private_key', '')
        }
        obj = AuthBook.objects.create(**kwargs)
        obj.set_auth(**auth_info)
        return obj
