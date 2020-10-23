from common.permissions import IsValidUser


class IsSystemAdminUser(IsValidUser):
    def has_permission(self, request, view):
        return super(IsSystemAdminUser, self).has_permission(request, view) and \
               request.user.is_sys_admin
