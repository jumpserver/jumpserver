from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from orgs.utils import tmp_to_root_org
from common.utils import get_object_or_none, lazyproperty
from users.models import User
from assets.models import Asset, SystemUser


__all__ = ['LoginAssetCheckSerializer']


class LoginAssetCheckSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=True, allow_null=False)
    asset_id = serializers.UUIDField(required=True, allow_null=False)
    system_user_id = serializers.UUIDField(required=True, allow_null=False)
    system_user_username = serializers.CharField(max_length=128, default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.asset = None
        self._system_user = None
        self._system_user_username = None

    def validate_user_id(self, user_id):
        self.user = self.validate_object_exist(User, user_id)
        return user_id

    def validate_asset_id(self, asset_id):
        self.asset = self.validate_object_exist(Asset, asset_id)
        return asset_id

    def validate_system_user_id(self, system_user_id):
        self._system_user = self.validate_object_exist(SystemUser, system_user_id)
        return system_user_id

    def validate_system_user_username(self, system_user_username):
        system_user_id = self.initial_data.get('system_user_id')
        system_user = self.validate_object_exist(SystemUser, system_user_id)
        if self._system_user.login_mode == SystemUser.LOGIN_MANUAL \
                and not system_user.username \
                and not system_user.username_same_with_user \
                and not system_user_username:
            error = 'Missing parameter: system_user_username'
            raise serializers.ValidationError(error)
        self._system_user_username = system_user_username
        return system_user_username

    @staticmethod
    def validate_object_exist(model, field_id):
        with tmp_to_root_org():
            obj = get_object_or_none(model, pk=field_id)
        if not obj:
            error = '{} Model object does not exist'.format(model.__name__)
            raise serializers.ValidationError(error)
        return obj

    @lazyproperty
    def system_user(self):
        if self._system_user.username_same_with_user:
            username = self.user.username
        elif self._system_user.login_mode == SystemUser.LOGIN_MANUAL:
            username = self._system_user_username
        else:
            username = self._system_user.username
        self._system_user.username = username
        return self._system_user

    @lazyproperty
    def org(self):
        return self.asset.org
