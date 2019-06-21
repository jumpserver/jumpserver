# -*- coding: utf-8 -*-
#

from .base import BaseBackend


class VaultBackend(BaseBackend):

    @classmethod
    def filter(cls, username=None, asset=None, latest=True):
        pass
