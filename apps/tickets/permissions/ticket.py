
from rest_framework import permissions


class IsAssignee(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.has_assignee(request.user)


class NotClosed(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return True
        return not obj.status_closed
