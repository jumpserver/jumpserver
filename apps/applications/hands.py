"""
    jumpserver.__app__.hands.py
    ~~~~~~~~~~~~~~~~~

    This app depends other apps api, function .. should be import or write mack here.

    Other module of this app shouldn't connect with other app.

    :copyright: (c) 2014-2018 by Jumpserver Team.
    :license: GPL v2, see LICENSE for more details.
"""


from common.permissions import AdminUserRequiredMixin
from common.permissions import IsAppUser, IsOrgAdmin, IsValidUser, IsOrgAdminOrAppUser
from users.models import User, UserGroup
