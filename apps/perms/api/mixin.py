# -*- coding: utf-8 -*-
#

from rest_framework.generics import get_object_or_404
from common.permissions import IsValidUser, IsOrgAdminOrAppUser
from common.utils import get_logger
from orgs.utils import set_to_root_org, set_current_org, get_current_org
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
        self.obj = self.get_obj()

    def get_obj(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            self.current_org = get_current_org()
            set_to_root_org()
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


