from rest_framework.generics import CreateAPIView

from accounts import serializers
from accounts.permissions import AccountTaskActionPermission
from accounts.tasks import (
    remove_accounts_task, verify_accounts_connectivity_task, push_accounts_to_assets_task
)
from assets.exceptions import NotSupportedTemporarilyError
from authentication.permissions import UserConfirmation, ConfirmType

__all__ = [
    'AccountsTaskCreateAPI',
]


class AccountsTaskCreateAPI(CreateAPIView):
    serializer_class = serializers.AccountTaskSerializer
    permission_classes = (AccountTaskActionPermission,)

    def get_permissions(self):
        act = self.request.data.get('action')
        if act == 'remove':
            self.permission_classes = [
                AccountTaskActionPermission,
                UserConfirmation.require(ConfirmType.PASSWORD)
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        data = serializer.validated_data
        accounts = data.get('accounts', [])
        params = data.get('params')
        account_ids = [str(a.id) for a in accounts]

        if data['action'] == 'push':
            task = push_accounts_to_assets_task.delay(account_ids, params)
        elif data['action'] == 'remove':
            gather_accounts = data.get('gather_accounts', [])
            gather_account_ids = [str(a.id) for a in gather_accounts]
            task = remove_accounts_task.delay(gather_account_ids)
        else:
            account = accounts[0]
            asset = account.asset
            if not asset.auto_config['ansible_enabled'] or \
                    not asset.auto_config['ping_enabled']:
                raise NotSupportedTemporarilyError()
            task = verify_accounts_connectivity_task.delay(account_ids)

        data = getattr(serializer, '_data', {})
        data["task"] = task.id
        setattr(serializer, '_data', data)
        return task
