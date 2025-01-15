# -*- coding: utf-8 -*-
#
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from rest_framework.request import Request

from common.utils.http import is_true
from common.utils import lazyproperty, is_uuid
from common.exceptions import JMSObjectDoesNotExist
from rbac.permissions import RBACPermission
from users.models import User
from perms.utils import UserPermTreeRefreshUtil

__all__ = ['SelfOrPKUserMixin', 'RebuildTreeMixin']


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


class RebuildTreeMixin:
    user: User
    request: Request

    def get(self, request, *args, **kwargs):
        UserPermTreeRefreshUtil(self.user).refresh_if_need(force=self.is_force_refresh_tree)
        return super().get(request, *args, **kwargs)

    @lazyproperty
    def is_force_refresh_tree(self):
        force = is_true(self.request.query_params.get('rebuild_tree'))
        if not force:
            force = self.compute_is_force_refresh()
        return force

    def compute_is_force_refresh(self):
        """ 5s 内连续刷新三次转为强制刷新 """
        force_timeout = 5
        force_max_count = 3
        force_cache_key = '{user_id}:{path}'.format(user_id=self.user.id, path=self.request.path)
        count = cache.get(force_cache_key, 1)
        if count >= force_max_count:
            force = True
            cache.delete(force_cache_key)
        else:
            force = False
            cache.set(force_cache_key, count + 1, force_timeout)
        return force
