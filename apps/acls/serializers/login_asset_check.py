from rest_framework import serializers

from common.utils import get_object_or_none
from orgs.utils import tmp_to_root_org
from users.models import User

__all__ = ['LoginAssetCheckSerializer']


class LoginAssetCheckSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=True, allow_null=False)
    asset_id = serializers.UUIDField(required=True, allow_null=False)
    account_username = serializers.CharField(max_length=128, default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.asset = None

    def validate_user_id(self, user_id):
        self.user = self.get_object(User, user_id)
        return user_id

    def validate_asset_id(self, asset_id):
        from assets.models import Asset
        self.asset = self.get_object(Asset, asset_id)
        return asset_id

    @staticmethod
    def get_object(model, pk):
        with tmp_to_root_org():
            obj = get_object_or_none(model, pk=pk)
        if obj:
            return obj
        error = '{} Model object does not exist'.format(model.__name__)
        raise serializers.ValidationError(error)
