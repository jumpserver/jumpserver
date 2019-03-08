# -*- coding: utf-8 -*-
#

from django.conf import settings

from .db import AuthBookBackend
from .vault import VaultBackend


def get_backend():
    if settings.ASSET_AUTH_VAULT:
        _backend = VaultBackend()
    else:
        _backend = AuthBookBackend()
    return _backend


backend = get_backend()
