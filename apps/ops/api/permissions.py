# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework import permissions


class AdminUserRequired(permissions.BasePermission):
    """
    Custom permission to only allow admin user to access the resource.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the admin role.
        return request.user.is_staff
