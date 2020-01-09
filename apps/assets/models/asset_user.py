# -*- coding: utf-8 -*-
#
from .authbook import AuthBook


class AssetUser(AuthBook):
    hostname = ""
    ip = ""
    backend = ""
    union_id = ""
    asset_username = ""

    class Meta:
        proxy = True
