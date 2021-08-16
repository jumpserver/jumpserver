from rest_framework import permissions


class IsAssignee(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.has_assignee(request.user)


class IsApplicant(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.applicant == request.user


class NotClosed(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return not obj.status_closed
