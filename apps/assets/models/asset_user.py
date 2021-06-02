# -*- coding: utf-8 -*-
#
from .authbook import AuthBook


class AssetUser(AuthBook):
    hostname = ""
    ip = ""
    backend = ""
    backend_display = ""
    union_id = ""
    asset_username = ""

    class Meta:
        proxy = True
