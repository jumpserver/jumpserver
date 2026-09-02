from rest_framework import permissions

from accounts.models import CredentialClientInstance, IntegrationApplication


def check_permissions(request):
    act = request.data.get('action')
    if act == 'push':
        code = 'accounts.push_account'
    elif act == 'remove':
        code = 'accounts.remove_account'
    else:
        code = 'accounts.verify_account'
    return request.user.has_perm(code)


class AccountTaskActionPermission(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        return super().has_permission(request, view) \
            and check_permissions(request)


class IsCredentialClient(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return isinstance(user, (IntegrationApplication, CredentialClientInstance)) \
            and user.is_authenticated
