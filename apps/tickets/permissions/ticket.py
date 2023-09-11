from rest_framework import permissions


class IsAssignee(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        return obj.has_current_assignee(request.user)


class IsApplicant(permissions.IsAuthenticated):

    def has_object_permission(self, request, view, obj):
        return obj.applicant == request.user
