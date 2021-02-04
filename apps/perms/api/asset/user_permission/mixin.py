# -*- coding: utf-8 -*-
#
from rest_framework.request import Request

from common.permissions import IsOrgAdminOrAppUser, IsValidUser
from common.utils import lazyproperty
from common.http import is_true
from orgs.utils import tmp_to_root_org
from users.models import User
from perms.utils.asset.user_permission import UserGrantedTreeRefreshController


class PermBaseMixin:
    user: User

    def get(self, request, *args, **kwargs):
        force = is_true(request.query_params.get('rebuild_tree'))
        controller = UserGrantedTreeRefreshController(self.user)
        controller.refresh_if_need(force)
        return super().get(request, *args, **kwargs)


class RoleAdminMixin(PermBaseMixin):
    permission_classes = (IsOrgAdminOrAppUser,)
    kwargs: dict

    @lazyproperty
    def user(self):
        user_id = self.kwargs.get('pk')
        return User.objects.get(id=user_id)


class RoleUserMixin(PermBaseMixin):
    permission_classes = (IsValidUser,)
    request: Request

    def get(self, request, *args, **kwargs):
        with tmp_to_root_org():
            return super().get(request, *args, **kwargs)

    @lazyproperty
    def user(self):
        return self.request.user
