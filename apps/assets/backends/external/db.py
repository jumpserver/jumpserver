# -*- coding: utf-8 -*-
#

from assets.models import AuthBook

from ..base import BaseBackend


class AuthBookBackend(BaseBackend):

    @classmethod
    def filter(cls, username=None, asset=None, latest=True):
        queryset = AuthBook.objects.all()
        if username is not None:
            queryset = queryset.filter(username=username)
        if asset:
            queryset = queryset.filter(asset=asset)
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
