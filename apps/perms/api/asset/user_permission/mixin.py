# -*- coding: utf-8 -*-
#
from rest_framework.request import Request

from common.permissions import IsOrgAdminOrAppUser, IsValidUser
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


class RoleAdminMixin(PermBaseMixin, _RoleAdminMixin):
    permission_classes = (IsOrgAdminOrAppUser,)


class RoleUserMixin(PermBaseMixin, _RoleUserMixin):
    permission_classes = (IsValidUser,)

    def get(self, request, *args, **kwargs):
        with tmp_to_root_org():
            return super().get(request, *args, **kwargs)
