# -*- coding: utf-8 -*-
#

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from assets.models import AuthBook

from .. import meta
from .base import BaseBackend


class AuthBookBackend(BaseBackend):

    def get(self, username, asset):
        queryset = self.filter(username, asset)
        if len(queryset) == 1:
            return queryset.first()

        elif len(queryset) == 0:
            msg = meta.EXCEPTION_MSG_NOT_EXIST.format(self.__class__.__name__)
            raise ObjectDoesNotExist(msg)

        else:
            msg = meta.EXCEPTION_MSG_MULTIPLE.format(self.__class__.__name__, len(queryset))
            raise MultipleObjectsReturned(msg)

    def filter(self, username=None, asset=None, latest=True):
        queryset = AuthBook.objects.all()
        if username:
            queryset = queryset.filter(username=username)
        if asset:
            queryset = queryset.filter(asset=asset)
        if latest:
            queryset = queryset.latest_version()
        return queryset

    def create(self, **kwargs):
        auth_info = {
            'password': kwargs.pop('password', ''),
            'public_key': kwargs.pop('public_key', ''),
            'private_key': kwargs.pop('private_key', '')
        }
        obj = AuthBook.objects.create(**kwargs)
        obj.set_auth(**auth_info)
        return obj
