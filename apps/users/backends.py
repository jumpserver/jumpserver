# -*- coding: utf-8 -*-
#

from rest_framework import authentication, exceptions, permissions
from rest_framework.compat import is_authenticated
from django.utils.translation import ugettext as _

from common.utils import unsign, get_object_or_none
from .hands import Terminal


class TerminalAuthentication(authentication.BaseAuthentication):
    keyword = 'Sign'
    model = Terminal

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
        name = unsign(sign, max_age=300)
        if name:
            terminal = get_object_or_none(self.model, name=name)
        else:
            raise exceptions.AuthenticationFailed(_('Invalid sign.'))

        if not terminal.is_active:
            raise exceptions.AuthenticationFailed(_('Terminal inactive or deleted.'))
        terminal.is_authenticated = True
        return terminal, None


class IsValidUser(permissions.IsAuthenticated, permissions.BasePermission):
    """Allows access to valid user, is active and not expired"""

    def has_permission(self, request, view):
        return super(IsValidUser, self).has_permission(request, view) \
               and request.user.is_valid


class IsTerminalUser(IsValidUser, permissions.BasePermission):
    """Allows access only to app user """

    def has_permission(self, request, view):
        return super(IsTerminalUser, self).has_permission(request, view) \
               and isinstance(request.user, Terminal)


class IsSuperUser(IsValidUser, permissions.BasePermission):
    """Allows access only to superuser"""

    def has_permission(self, request, view):
        return super(IsSuperUser, self).has_permission(request, view) \
               and request.user.is_superuser


class IsSuperUserOrTerminalUser(IsValidUser, permissions.BasePermission):
    """Allows access between superuser and app user"""

    def has_permission(self, request, view):
        return super(IsSuperUserOrTerminalUser, self).has_permission(request, view) \
               and (request.user.is_superuser or request.user.is_terminal)


if __name__ == '__main__':
    pass
