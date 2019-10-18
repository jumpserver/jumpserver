# -*- coding: utf-8 -*-
#

from rest_framework.generics import get_object_or_404
from common.permissions import IsValidUser, IsOrgAdminOrAppUser
from common.utils import get_logger
from orgs.utils import set_to_root_org, get_current_org, set_current_org, tmp_to_root_org
from ..hands import User, UserGroup


logger = get_logger(__name__)

__all__ = [
    'UserPermissionMixin', 'UserGroupPermissionMixin',
]


class UserPermissionMixin:
    permission_classes = (IsOrgAdminOrAppUser,)
    current_org = None
    obj = None

    def initial(self, *args, **kwargs):
        super().initial(*args, *kwargs)
        self.current_org = get_current_org()
        set_to_root_org()
        self.obj = self.get_obj()

    # def dispatch(self, request, *args, **kwargs):
    #     """不能这么做，校验权限时拿不到组织了"""
    #     with tmp_to_root_org():
    #         return super().dispatch(request, *args, **kwargs)

    # def get(self, request, *args, **kwargs):
    #     """有的api重写了get方法"""
    #     with tmp_to_root_org():
    #         return super().get(request, *args, **kwargs)

    def get_obj(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        org = getattr(self, 'current_org', None)
        if org:
            set_current_org(org)
        return response


class UserGroupPermissionMixin:
    obj = None

    def get_obj(self):
        user_group_id = self.kwargs.get('pk', '')
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        return user_group


