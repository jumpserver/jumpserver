from accounts.models import AccountTemplate, Account
from assets.models import Asset
from common.serializers import SecretReadableMixin
from .base import BaseAccountSerializer


class AccountTemplateSerializer(BaseAccountSerializer):
    class Meta(BaseAccountSerializer.Meta):
        model = AccountTemplate

    @staticmethod
    def bulk_update_accounts(instance, diff):
        accounts = Account.objects.filter(source_id=instance.id)
        if not accounts:
            return

        secret_type = diff.pop('secret_type', None)
        diff.pop('secret', None)
        update_accounts = []
        for account in accounts:
            for field, value in diff.items():
                setattr(account, field, value)
                update_accounts.append(account)
        if update_accounts:
            Account.objects.bulk_update(update_accounts, diff.keys())

        if secret_type is None:
            return

        update_accounts = []
        asset_ids = accounts.values_list('asset_id', flat=True)
        secret_type_supports = Asset.get_secret_type_assets(asset_ids, secret_type)
        asset_ids_supports = [asset.id for asset in secret_type_supports]
        for account in accounts:
            asset_id = account.asset_id
            if asset_id not in asset_ids_supports:
                continue
            account.secret_type = secret_type
            account.secret = instance.secret
            update_accounts.append(account)
        if update_accounts:
            Account.objects.bulk_update(update_accounts, ['secret', 'secret_type'])

    def update(self, instance, validated_data):
        diff = {
            k: v for k, v in validated_data.items()
            if getattr(instance, k) != v
        }
        instance = super().update(instance, validated_data)
        self.bulk_update_accounts(instance, diff)
        return instance


class AccountTemplateSecretSerializer(SecretReadableMixin, AccountTemplateSerializer):
    class Meta(AccountTemplateSerializer.Meta):
        extra_kwargs = {
            'secret': {'write_only': False},
        }
