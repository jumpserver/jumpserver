# -*- coding: utf-8 -*-
#

from ..models import AdminUser
from .asset_user import AssetUserBackend


class AdminUserBackend(AssetUserBackend):
    model = AdminUser
    backend = 'AdminUser'
