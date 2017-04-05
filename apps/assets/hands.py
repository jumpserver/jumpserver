"""
    jumpserver.__app__.hands.py
    ~~~~~~~~~~~~~~~~~

    This app depends other apps api, function .. should be import or write mack here.

    Other module of this app shouldn't connect with other app.

    :copyright: (c) 2014-2017 by Jumpserver Team.
    :license: GPL v2, see LICENSE for more details.
"""


from users.utils import AdminUserRequiredMixin
from users.permissions import IsAppUser, IsSuperUser, IsValidUser
from users.models import User, UserGroup
from perms.utils import get_user_granted_assets
from perms.tasks import push_users