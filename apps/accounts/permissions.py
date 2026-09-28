from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from authentication.permissions import UserConfirmation, ConfirmType


RISK_ACTION_PERMISSIONS = {
    'ignore': (),
    'reopen': (),
    'close': (),
    'disable_remote': ('accounts.remove_account',),
    'delete_remote': ('accounts.remove_account',),
    'delete_account': ('accounts.delete_account', 'accounts.delete_gatheredaccount'),
    'delete_both': (
        'accounts.remove_account', 'accounts.delete_account', 'accounts.delete_gatheredaccount',
    ),
    'add_account': ('accounts.add_account',),
    'change_password': ('accounts.add_changesecretexecution',),
    'change_password_add': (
        'accounts.add_account', 'accounts.push_account',
    ),
}
RISK_ACTION_CONFIRMATIONS = {
    'disable_remote': ConfirmType.PASSWORD,
    'delete_remote': ConfirmType.PASSWORD,
    'delete_account': ConfirmType.PASSWORD,
    'delete_both': ConfirmType.PASSWORD,
    'change_password': ConfirmType.MFA,
    'change_password_add': ConfirmType.MFA,
}


def check_risk_action_permissions(request, action):
    required = RISK_ACTION_PERMISSIONS.get(action)
    if request is None or required is None:
        raise PermissionDenied()
    user = request.user
    if not user.is_authenticated or not user.is_valid or not user.has_perms(required):
        raise PermissionDenied()
    confirm_type = RISK_ACTION_CONFIRMATIONS.get(action)
    if confirm_type:
        confirmation = UserConfirmation.require(confirm_type)()
        if not confirmation.has_permission(request, None):
            raise PermissionDenied()

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
