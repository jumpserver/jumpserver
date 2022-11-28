from rest_framework import serializers
from orgs.utils import tmp_to_root_org
from common.utils import get_object_or_none, lazyproperty
from users.models import User
from assets.models import Asset, Account

__all__ = ['LoginAssetCheckSerializer']


class LoginAssetCheckSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=True, allow_null=False)
    asset_id = serializers.UUIDField(required=True, allow_null=False)
    account_username = serializers.CharField(max_length=128, default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.asset = None
        self.username = None

    def validate_user_id(self, user_id):
        self.user = self.validate_object_exist(User, user_id)
        return user_id

    def validate_asset_id(self, asset_id):
        self.asset = self.validate_object_exist(Asset, asset_id)
        return asset_id

    @staticmethod
    def validate_object_exist(model, field_id):
        with tmp_to_root_org():
            obj = get_object_or_none(model, pk=field_id)
        if not obj:
            error = '{} Model object does not exist'.format(model.__name__)
            raise serializers.ValidationError(error)
        return obj

    def validate_account_username(self, account_username):
        asset_id = self.initial_data.get('asset_id')
        account = Account.objects.filter(
            username=account_username, asset_id=asset_id
        ).first()
        if not account:
            error = 'Account username does not exist'
            raise serializers.ValidationError(error)
        self.username = account_username
        return account_username

    @lazyproperty
    def org(self):
        return self.asset.org
