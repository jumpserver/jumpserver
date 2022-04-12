# -*- coding: utf-8 -*-
#

from common.mixins.api import RoleAdminMixin as _RoleAdminMixin
from common.mixins.api import RoleUserMixin as _RoleUserMixin
from orgs.utils import tmp_to_root_org


class AppRoleAdminMixin(_RoleAdminMixin):
    rbac_perms = (
        ('list', 'perms.view_userapp'),
        ('retrieve', 'perms.view_userapps'),
        ('get_tree', 'perms.view_userapps'),
        ('GET', 'perms.view_userapps'),
    )


class AppRoleUserMixin(_RoleUserMixin):
    rbac_perms = (
        ('list', 'perms.view_myapps'),
        ('retrieve', 'perms.view_myapps'),
        ('get_tree', 'perms.view_myapps'),
        ('GET', 'perms.view_myapps'),
    )
