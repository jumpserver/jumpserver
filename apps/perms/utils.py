from __future__ import absolute_import, unicode_literals

from .models import AssetPermission
from .hands import User, UserGroup, Asset, AssetGroup, SystemUser
from common.utils import combine_seq


def get_asset_groups_denied_by_user_group(user_group):
    pass


def get_asset_groups_granted_by_user_group(user_group):
    """Return asset groups granted of the user group

        :param user_group: Instance of :class: ``UserGroup``
        :return: {asset_group1: {system_user1, }, asset_group2: {system_user1, system_user2]}
    """
    asset_groups = {}

    if not isinstance(user_group, UserGroup):
        return asset_groups

    asset_permissions = user_group.asset_permissions.all()
    for asset_permission in asset_permissions:
        if not asset_permission.is_valid:
            continue
        for asset_group in asset_permission.asset_groups.all():
            if asset_group in asset_groups:
                asset_groups[asset_group].union(set(asset_permission.system_users.all()))
            else:
                asset_groups[asset_group] = set(asset_permission.system_users.all())
    return asset_groups


def get_assets_granted_by_user_group(user_group):
    """Return assets granted of the user group

        :param user_group: Instance of :class: ``UserGroup``
        :return: {asset1: {system_user1, }, asset1: {system_user1, system_user2]}
    """
    assets = {}
    if not isinstance(user_group, UserGroup):
        return assets

    asset_permissions = user_group.asset_permissions.all()
    for asset_permission in asset_permissions:
        for asset in asset_permission.get_granted_assets:
            if asset in assets:
                pass


def get_asset_groups_granted_by_user(user):
    """Return asset groups granted of the user

    :param user: Instance of :class: ``User``
    :return: {asset_group: {system_user1, }, asset_group2: {system_user1, system_user2]}
    """
    asset_groups = {}

    if not isinstance(user, User):
        return asset_groups

    asset_permissions = user.asset_permissions.all()

    for asset_permission in asset_permissions:
        for asset_group in asset_permission.asset_groups.all():
            if asset_group in asset_groups:
                asset_groups[asset_group].union(set(asset_permission.system_users.all()))
            else:
                asset_groups[asset_group] = set(asset_permission.system_users.all())

    return asset_groups


def get_assets_granted_by_user(user):
    """Return all assets granted of the user

    :param user: Instance of :class: ``User``
    :return: {asset1: {system_user1, system_user2}, asset2: {...}}
    """
    pass


def get_user_groups_granted_in_asset(asset):
    pass


def get_users_granted_in_asset(asset):
    pass


def get_user_groups_granted_in_asset_group(asset):
    pass


def get_users_granted_in_asset_group(asset):
    pass
