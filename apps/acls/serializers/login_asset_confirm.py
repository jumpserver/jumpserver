from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from orgs.utils import tmp_to_root_org, tmp_to_org
from common.utils import get_object_or_none, lazyproperty
from users.models import User
from assets.models import Asset, SystemUser


class LoginAssetConfirmCheckSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=True, allow_null=False)
    asset_id = serializers.UUIDField(required=True, allow_null=False)
    system_user_id = serializers.UUIDField(required=True, allow_null=False)
    system_user_username = serializers.CharField(max_length=128, default='')

    def validate_user_id(self, user_id):
        with tmp_to_root_org():
            self.validate_object_exist(User, user_id)
        return user_id

    def validate_asset_id(self, asset_id):
        with tmp_to_root_org():
            self.validate_object_exist(Asset, asset_id)
        return asset_id

    def validate_system_user_id(self, system_user_id):
        asset_id = self.initial_data.get('asset_id')
        self.validate_asset_id(asset_id)
        with tmp_to_root_org():
            asset = get_object_or_none(Asset, pk=asset_id)
        with tmp_to_org(asset.org):
            self.validate_object_exist(SystemUser, system_user_id)
        return system_user_id

    def validate_system_user_username(self, system_user_username):
        asset_id = self.initial_data.get('asset_id')
        self.validate_asset_id(asset_id)
        with tmp_to_root_org():
            asset = get_object_or_none(Asset, pk=asset_id)

        system_user_id = self.initial_data.get('system_user_id')
        self.validate_system_user_id(system_user_id)
        with tmp_to_org(asset.org):
            system_user = get_object_or_none(SystemUser, pk=system_user_id)

        if system_user.login_mode == SystemUser.LOGIN_MANUAL \
                and not self.system_user.username_same_with_user \
                and not system_user_username:
            error = 'Missing parameter: system_user_username'
            raise serializers.ValidationError(error)
        return system_user_username

    @staticmethod
    def validate_object_exist(model, field_id):
        obj = get_object_or_none(model, pk=field_id)
        if not obj:
            error = '{} Model object does not exist'.format(model.__name__)
            raise serializers.ValidationError(error)

    @lazyproperty
    def user(self):
        user_id = self.validated_data['user_id']
        with tmp_to_root_org():
            obj = get_object_or_none(User, pk=user_id)
        return obj

    @lazyproperty
    def asset(self):
        asset_id = self.validated_data['asset_id']
        with tmp_to_root_org():
            obj = get_object_or_none(Asset, pk=asset_id)
        return obj

    @lazyproperty
    def system_user(self):
        system_user_id = self.validated_data['system_user_id']
        with tmp_to_org(self.asset.org):
            obj = get_object_or_none(SystemUser, pk=system_user_id)
        username = self.get_system_user_username(system_user=obj)
        obj.username = username
        return obj

    def get_system_user_username(self, system_user):
        if system_user.username_same_with_user:
            return self.user.username
        elif system_user.login_mode == SystemUser.LOGIN_MANUAL:
            return self.validated_data['system_user_username']
        else:
            return system_user.username


class LoginAssetConfirmStatusSerializer(serializers.Serializer):
    pass
