# -*- coding: utf-8 -*-
#
from rest_framework.request import Request

from common.permissions import IsOrgAdminOrAppUser, IsValidUser
from common.utils import lazyproperty
from orgs.utils import tmp_to_root_org
from users.models import User
from perms.models import UserGrantedMappingNode


class UserNodeGrantStatusDispatchMixin:

    @staticmethod
    def get_mapping_node_by_key(key, user):
        return UserGrantedMappingNode.objects.get(key=key, user=user)

    def dispatch_get_data(self, key, user):
        status = UserGrantedMappingNode.get_node_granted_status(key, user)
        if status == UserGrantedMappingNode.GRANTED_DIRECT:
            return self.get_data_on_node_direct_granted(key)
        elif status == UserGrantedMappingNode.GRANTED_INDIRECT:
            return self.get_data_on_node_indirect_granted(key)
        else:
            return self.get_data_on_node_not_granted(key)

    def get_data_on_node_direct_granted(self, key):
        raise NotImplementedError

    def get_data_on_node_indirect_granted(self, key):
        raise NotImplementedError

    def get_data_on_node_not_granted(self, key):
        raise NotImplementedError


class ForAdminMixin:
    permission_classes = (IsOrgAdminOrAppUser,)
    kwargs: dict

    @lazyproperty
    def user(self):
        user_id = self.kwargs.get('pk')
        return User.objects.get(id=user_id)


class ForUserMixin:
    permission_classes = (IsValidUser,)
    request: Request

    def get(self, request, *args, **kwargs):
        with tmp_to_root_org():
            return super().get(request, *args, **kwargs)

    @lazyproperty
    def user(self):
        return self.request.user
