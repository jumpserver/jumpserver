# -*- coding: utf-8 -*-
#
from rest_framework.request import Request

from common.http import is_true
from common.mixins.api import RoleAdminMixin as _RoleAdminMixin
from common.mixins.api import RoleUserMixin as _RoleUserMixin
from orgs.utils import tmp_to_root_org
from users.models import User
from perms.utils.asset.user_permission import UserGrantedTreeRefreshController


class PermBaseMixin:
    user: User

    def get(self, request: Request, *args, **kwargs):
        force = is_true(request.query_params.get('rebuild_tree'))
        controller = UserGrantedTreeRefreshController(self.user)
        controller.refresh_if_need(force)
        return super().get(request, *args, **kwargs)


class AssetRoleAdminMixin(PermBaseMixin, _RoleAdminMixin):
    rbac_perms = (
        ('list', 'perms.view_userassets'),
        ('retrieve', 'perms.view_userassets'),
        ('get_tree', 'perms.view_userassets'),
        ('GET', 'perms.view_userassets'),
    )


class AssetRoleUserMixin(PermBaseMixin, _RoleUserMixin):
    rbac_perms = (
        ('list', 'perms.view_myassets'),
        ('retrieve', 'perms.view_myassets'),
        ('get_tree', 'perms.view_myassets'),
        ('GET', 'perms.view_myassets'),
    )
