# -*- coding: utf-8 -*-
#

from .base import BaseBackend


class VaultBackend(BaseBackend):

    def get(self, username, asset):
        pass

    def filter(self, username=None, asset=None, latest=True):
        pass

    def create(self, **kwargs):
        pass
