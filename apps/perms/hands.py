# ~*~ coding: utf-8 ~*~
#

from users.utils import AdminUserRequiredMixin
from users.models import User, UserGroup
from assets.models import Asset, AssetGroup, SystemUser
from assets.serializers import AssetGrantedSerializer, AssetGroupSerializer


def push_system_user(assets, system_user):
    print('Push system user %s' % system_user.name)
    for asset in assets:
        print('\tAsset: %s' % asset.ip)


