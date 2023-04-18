from django.db.utils import IntegrityError

from accounts.models import AccountTemplate, Account
from assets.models import Asset
from common.serializers import SecretReadableMixin
from .base import BaseAccountSerializer


class AccountTemplateSerializer(BaseAccountSerializer):
    class Meta(BaseAccountSerializer.Meta):
        model = AccountTemplate

    @staticmethod
    def account_save(data, account):
        for field, value in data.items():
            setattr(account, field, value)
        try:
            account.save(update_fields=list(data.keys()))
        except IntegrityError:
            pass

    # TODO 数据库访问的太多了 后期优化
    def bulk_update_accounts(self, instance, diff):
        accounts = Account.objects.filter(source_id=instance.id)
        if not accounts:
            return

        diff.pop('secret', None)
        name = diff.pop('name', None)
        username = diff.pop('username', None)
        secret_type = diff.pop('secret_type', None)
        update_accounts = []
        for account in accounts:
            for field, value in diff.items():
                setattr(account, field, value)
                update_accounts.append(account)

        if update_accounts:
            Account.objects.bulk_update(update_accounts, diff.keys())

        if name:
            for account in accounts:
                data = {'name': name}
                self.account_save(data, account)

        if secret_type and username:
            asset_ids_supports = self.get_asset_ids_supports(accounts, secret_type)
            for account in accounts:
                asset_id = account.asset_id
                if asset_id not in asset_ids_supports:
                    data = {'username': username}
                    self.account_save(data, account)
                    continue
                data = {'username': username, 'secret_type': secret_type, 'secret': instance.secret}
                self.account_save(data, account)
        elif secret_type:
            asset_ids_supports = self.get_asset_ids_supports(accounts, secret_type)
            for account in accounts:
                asset_id = account.asset_id
                if asset_id not in asset_ids_supports:
                    continue
                data = {'secret_type': secret_type, 'secret': instance.secret}
                self.account_save(data, account)
        elif username:
            for account in accounts:
                data = {'username': username}
                self.account_save(data, account)

    @staticmethod
    def get_asset_ids_supports(accounts, secret_type):
        asset_ids = accounts.values_list('asset_id', flat=True)
        secret_type_supports = Asset.get_secret_type_assets(asset_ids, secret_type)
        return [asset.id for asset in secret_type_supports]

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
