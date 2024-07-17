from rest_framework import permissions

from common.utils import get_logger

logger = get_logger(__file__)

__all__ = ['IsSessionAssignee']


class IsSessionAssignee(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if not request.user:
            return False
        if request.user.is_anonymous:
            return False
        if view.action == 'retrieve':
            # Why return True? please refer to the issue: #11678
            return True
        return False

    def has_object_permission(self, request, view, obj):
        try:
            return obj.ticket_relation.first().ticket.has_all_assignee(request.user)
        except:
            return False
