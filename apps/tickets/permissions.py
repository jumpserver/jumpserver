# -*- coding: utf-8 -*-
#

from rest_framework.permissions import BasePermission


class IsAssignee(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.is_assignee(request.user)
