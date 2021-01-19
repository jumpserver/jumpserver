
from rest_framework import permissions


class IsAssignee(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.has_assignee(request.user)


class IsAssigneeOrApplicant(IsAssignee):

    def has_object_permission(self, request, view, obj):
        return super().has_object_permission(request, view, obj) or obj.applicant == request.user


class NotClosed(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return not obj.status_closed
