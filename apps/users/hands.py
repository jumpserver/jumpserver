"""
    jumpserver.__app__.hands.py
    ~~~~~~~~~~~~~~~~~

    This app depends other apps api, function .. should be import or write mack here.

    Other module of this app shouldn't connect with other app.

    :copyright: (c) 2014-2018 by JumpServer Team.
    :license: GPL v2, see LICENSE for more details.
"""

# from terminal.models import Terminal
# from users.models import User
# from perms.models import AssetPermission
# from perms.utils import get_user_granted_assets, get_user_granted_asset_groups
from assets.models import Asset, SystemUser
