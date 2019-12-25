# -*- coding: utf-8 -*-
#
from .base import BaseUser


class AssetUser(BaseUser):
    hostname = ""
    ip = ""
    asset_id = ""
    score = 0
    backend = ""
    union_id = ""
    asset_username = ""
    version = 0

    class Meta:
        abstract = True
