from django.db.models import Count
from django.utils import timezone
from rest_framework import serializers

from accounts.models import AccountTemplate, Account
from assets.models import Asset
from common.serializers import SecretReadableMixin
from .base import BaseAccountSerializer


class AccountTemplateSerializer(BaseAccountSerializer):
    is_sync_account = serializers.BooleanField(default=False, write_only=True)
    _is_sync_account = False

    class Meta(BaseAccountSerializer.Meta):
        model = AccountTemplate
        fields = BaseAccountSerializer.Meta.fields + ['is_sync_account']

    @staticmethod
    def bulk_update_accounts(accounts, data):
        history_model = Account.history.model
        account_ids = accounts.values_list('id', flat=True)
        history_accounts = history_model.objects.filter(id__in=account_ids)
        account_id_count_map = {
            str(i['id']): i['count']
            for i in history_accounts.values('id').order_by('id')
            .annotate(count=Count(1)).values('id', 'count')
        }

        for account in accounts:
            account_id = str(account.id)
            account.version = account_id_count_map.get(account_id) + 1
            for k, v in data.items():
                setattr(account, k, v)
        Account.objects.bulk_update(accounts, ['version', 'secret'])

    def bulk_create_history_accounts(self, accounts):
        history_model = Account.history.model
        history_account_objs = []
        for account in accounts:
            history_account_objs.append(
                history_model(
                    id=account.id,
                    version=account.version,
                    secret=account.secret,
                    secret_type=account.secret_type,
                    history_user_id=self.context['request'].user.id,
                    history_date=timezone.now()
                )
            )
        history_model.objects.bulk_create(history_account_objs)

    def sync_accounts(self, instance, diff):
        if not self._is_sync_account:
            return

        accounts = Account.objects.filter(source_id=instance.id)
        if not accounts:
            return

        secret = diff.pop('secret', None)
        secret_type = diff.pop('secret_type', None)
        if secret_type:
            asset_ids_supports = self.get_asset_ids_supports(accounts, secret_type)
            accounts = accounts.filter(asset_id__in=asset_ids_supports)
            if not accounts:
                return
            accounts.update(secret_type=secret_type)

        if secret:
            self.bulk_update_accounts(accounts, {'secret': instance.secret})
            self.bulk_create_history_accounts(accounts)

    @staticmethod
    def get_asset_ids_supports(accounts, secret_type):
        asset_ids = accounts.values_list('asset_id', flat=True)
        secret_type_supports = Asset.get_secret_type_assets(asset_ids, secret_type)
        return [str(asset.id) for asset in secret_type_supports]

    def validate(self, attrs):
        self._is_sync_account = attrs.pop('is_sync_account', None)
        attrs = super().validate(attrs)
        return attrs

    def update(self, instance, validated_data):
        diff = {
            k: v for k, v in validated_data.items()
            if getattr(instance, k) != v
        }
        instance = super().update(instance, validated_data)
        self.sync_accounts(instance, diff)
        return instance


class AccountTemplateSecretSerializer(SecretReadableMixin, AccountTemplateSerializer):
    class Meta(AccountTemplateSerializer.Meta):
        extra_kwargs = {
            'secret': {'write_only': False},
        }
