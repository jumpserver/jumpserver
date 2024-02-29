from django.db.models import Q
from rest_framework.generics import CreateAPIView

from accounts import serializers
from accounts.models import Account
from accounts.permissions import AccountTaskActionPermission
from accounts.tasks import (
    remove_accounts_task, verify_accounts_connectivity_task, push_accounts_to_assets_task
)
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

    @staticmethod
    def get_account_ids(data, action):
        account_type = 'gather_accounts' if action == 'remove' else 'accounts'
        accounts = data.get(account_type, [])
        account_ids = [str(a.id) for a in accounts]

        if action == 'remove':
            return account_ids

        assets = data.get('assets', [])
        asset_ids = [str(a.id) for a in assets]
        ids = Account.objects.filter(
            Q(id__in=account_ids) | Q(asset_id__in=asset_ids)
        ).distinct().values_list('id', flat=True)
        return [str(_id) for _id in ids]

    def perform_create(self, serializer):
        data = serializer.validated_data
        action = data['action']
        ids = self.get_account_ids(data, action)

        if action == 'push':
            task = push_accounts_to_assets_task.delay(ids, data.get('params'))
        elif action == 'remove':
            task = remove_accounts_task.delay(ids)
        elif action == 'verify':
            task = verify_accounts_connectivity_task.delay(ids)
        else:
            raise ValueError(f"Invalid action: {action}")

        data = getattr(serializer, '_data', {})
        data["task"] = task.id
        setattr(serializer, '_data', data)
        return task
