from rest_framework import permissions

from tickets.errors import TicketStateChanged


class IsAssignee(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        if obj.has_current_assignee(request.user):
            return True
        if view.action in ('approve', 'reject') and obj.has_all_assignee(request.user):
            raise TicketStateChanged
        return False


class IsApplicant(permissions.IsAuthenticated):

    def has_object_permission(self, request, view, obj):
        return obj.applicant == request.user
