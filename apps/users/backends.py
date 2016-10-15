# -*- coding: utf-8 -*-
#

from rest_framework import authentication, exceptions, permissions
from rest_framework.compat import is_authenticated
from django.utils.translation import ugettext as _

from common.utils import unsign, get_object_or_none
from .models import User


class AppSignAuthentication(authentication.BaseAuthentication):
    keyword = 'Sign'
    model = User

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid sign header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid sign header. Sign string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            sign = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Sign string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)
        return self.authenticate_credentials(sign)

    def authenticate_credentials(self, sign):
        app = unsign(sign, max_age=300)
        if app:
            user = get_object_or_none(self.model, username=app, role='App')
        else:
            raise exceptions.AuthenticationFailed(_('Invalid sign.'))

        if not user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))
        return user, None


class IsValidUser(permissions.IsAuthenticated, permissions.BasePermission):
    """Allows access to valid user, is active and not expired"""

    def has_permission(self, request, view):
        return super(IsValidUser, self).has_permission(request, view) \
               and request.user.is_valid


class IsAppUser(IsValidUser, permissions.BasePermission):
    """Allows access only to app user """

    def has_permission(self, request, view):
        return super(IsAppUser, self).has_permission(request, view) \
               and request.user.is_app_user


class IsSuperUser(IsValidUser, permissions.BasePermission):
    """Allows access only to superuser"""

    def has_permission(self, request, view):
        return super(IsSuperUser, self).has_permission(request, view) \
               and request.user.is_superuser


class IsSuperUserOrAppUser(IsValidUser, permissions.BasePermission):
    """Allows access between superuser and app user"""

    def has_permission(self, request, view):
        return super(IsSuperUserOrAppUser, self).has_permission(request, view) \
               and (request.user.is_superuser or request.user.is_app_user)


if __name__ == '__main__':
    pass
