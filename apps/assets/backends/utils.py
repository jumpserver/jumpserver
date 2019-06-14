# -*- coding: utf-8 -*-
#

# from django.conf import settings

from .db import AuthBookBackend
# from .vault import VaultBackend


def get_backend():
    default_backend = AuthBookBackend

    # if settings.BACKEND_ASSET_USER_AUTH_VAULT:
    #     return VaultBackend

    return default_backend
