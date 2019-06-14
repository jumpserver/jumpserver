# -*- coding: utf-8 -*-
#

from ..base import BaseBackend


class VaultBackend(BaseBackend):

    @classmethod
    def get(cls, username, asset):
        pass

    @classmethod
    def filter(cls, username=None, asset=None, latest=True):
        pass

    @classmethod
    def create(cls, **kwargs):
        pass
