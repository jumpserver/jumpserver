#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import base64

from django.core.cache import cache
from django.conf import settings
from django.utils.translation import ugettext as _
from rest_framework import authentication, exceptions, permissions
from rest_framework.compat import is_authenticated

from common.utils import signer, get_object_or_none
from .hands import Terminal
from .models import User


class IsValidUser(permissions.IsAuthenticated, permissions.BasePermission):
    """Allows access to valid user, is active and not expired"""

    def has_permission(self, request, view):
        return super(IsValidUser, self).has_permission(request, view) \
               and request.user.is_valid


class IsAppUser(IsValidUser, permissions.BasePermission):
    """Allows access only to app user """

    def has_permission(self, request, view):
        return super(IsAppUser, self).has_permission(request, view) \
               and request.user.is_app


class IsSuperUser(IsValidUser, permissions.BasePermission):
    """Allows access only to superuser"""

    def has_permission(self, request, view):
        return super(IsSuperUser, self).has_permission(request, view) \
               and request.user.is_superuser


class IsSuperUserOrAppUser(IsValidUser, permissions.BasePermission):
    """Allows access between superuser and app user"""

    def has_permission(self, request, view):
        return super(IsSuperUserOrAppUser, self).has_permission(request, view) \
               and (request.user.is_superuser or request.user.is_app)


if __name__ == '__main__':
    pass
