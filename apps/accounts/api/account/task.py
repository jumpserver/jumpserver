from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from accounts import serializers
from accounts.tasks import verify_accounts_connectivity_task, push_accounts_to_assets_task
from assets.exceptions import NotSupportedTemporarilyError

__all__ = [
    'AccountsTaskCreateAPI',
]


class AccountsTaskCreateAPI(CreateAPIView):
    serializer_class = serializers.AccountTaskSerializer

    def check_permissions(self, request):
        act = request.data.get('action')
        if act == 'push':
            code = 'accounts.push_account'
        else:
            code = 'accounts.verify_account'
        return request.user.has_perm(code)

    def perform_create(self, serializer):
        data = serializer.validated_data
        accounts = data.get('accounts', [])
        params = data.get('params')
        account_ids = [str(a.id) for a in accounts]

        if data['action'] == 'push':
            task = push_accounts_to_assets_task.delay(account_ids, params)
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

    def get_exception_handler(self):
        def handler(e, context):
            return Response({"error": str(e)}, status=400)

        return handler
