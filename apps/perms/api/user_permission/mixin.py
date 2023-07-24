# -*- coding: utf-8 -*-
#
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework.request import Request

from common.exceptions import JMSObjectDoesNotExist
from common.utils import is_uuid
from rbac.permissions import RBACPermission
from users.models import User

__all__ = ['SelfOrPKUserMixin']


class SelfOrPKUserMixin:
    kwargs: dict
    request: Request
    permission_classes = (RBACPermission,)

    def get_rbac_perms(self):
        if self.request_user_is_self():
            return self.self_rbac_perms
        else:
            return self.admin_rbac_perms

    @property
    def self_rbac_perms(self):
        return (
            ('list', 'perms.view_myassets'),
            ('retrieve', 'perms.view_myassets'),
            ('get_tree', 'perms.view_myassets'),
            ('GET', 'perms.view_myassets'),
            ('OPTIONS', 'perms.view_myassets'),
        )

    @property
    def admin_rbac_perms(self):
        return (
            ('list', 'perms.view_userassets'),
            ('retrieve', 'perms.view_userassets'),
            ('get_tree', 'perms.view_userassets'),
            ('GET', 'perms.view_userassets'),
            ('OPTIONS', 'perms.view_userassets'),
        )

    @property
    def user(self):
        if self.request_user_is_self():
            user = self.request.user
        elif is_uuid(self.kwargs.get('user')):
            user = get_object_or_404(User, pk=self.kwargs.get('user'))
        elif hasattr(self, 'swagger_fake_view'):
            user = self.request.user
        else:
            raise JMSObjectDoesNotExist(object_name=_('User'))
        return user

    def request_user_is_self(self):
        return self.kwargs.get('user') in ['my', 'self']
