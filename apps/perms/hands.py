# ~*~ coding: utf-8 ~*~
#

from users.utils import AdminUserRequiredMixin
from users.models import User, UserGroup
from assets.models import Asset, AssetGroup, SystemUser


def associate_system_users_with_assets(system_users, assets, asset_groups):
    for asset in assets:
        asset.system_users.add(*tuple(system_users))

    for asset_group in asset_groups:
        asset_group.system_users.add(*tuple(system_users))
