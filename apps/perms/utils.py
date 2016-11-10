from __future__ import absolute_import, unicode_literals

from common.utils import setattr_bulk
from .hands import User, UserGroup, Asset, AssetGroup, SystemUser


def get_user_group_granted_asset_groups(user_group):
    """Return asset groups granted of the user group

     :param user_group: Instance of :class: ``UserGroup``
     :return: {asset_group1: {system_user1, }, asset_group2: {system_user1, system_user2]}
    """
    asset_groups = {}
    asset_permissions = user_group.asset_permissions.all()

    for asset_permission in asset_permissions:
        if not asset_permission.is_valid:
            continue
        for asset_group in asset_permission.asset_groups.all():
            if asset_group in asset_groups:
                asset_groups[asset_group] |= set(asset_permission.system_users.all())
            else:
                asset_groups[asset_group] = set(asset_permission.system_users.all())

    return asset_groups


def get_user_group_granted_assets(user_group):
    """Return assets granted of the user group

    :param user_group: Instance of :class: ``UserGroup``
    :return: {asset1: {system_user1, }, asset1: {system_user1, system_user2]}
    """
    assets = {}
    asset_permissions = user_group.asset_permissions.all()

    for asset_permission in asset_permissions:
        if not asset_permission.is_valid:
            continue
        for asset in asset_permission.get_granted_assets():
            if asset in assets:
                assets[asset] |= set(asset_permission.system_users.all())
            else:
                assets[asset] = set(asset_permission.system_users.all())
    return assets


def get_user_granted_asset_groups_direct(user):
    """Return asset groups granted of the user direct nor inherit from user group

        :param user: Instance of :class: ``User``
        :return: {asset_group: {system_user1, }, asset_group2: {system_user1, system_user2]}
        """
    asset_groups = {}
    asset_permissions_direct = user.asset_permissions.all()

    for asset_permission in asset_permissions_direct:
        if not asset_permission.is_valid:
            continue
        for asset_group in asset_permission.asset_groups.all():
            if asset_group in asset_groups:
                asset_groups[asset_group] |= set(asset_permission.system_users.all())
            else:
                setattr(asset_group, 'is_inherit_from_user_group', False)
                asset_groups[asset_group] = set(asset_permission.system_users.all())

    return asset_groups


def get_user_granted_asset_groups_inherit_from_user_groups(user):
    """Return asset groups granted of the user and inherit from user group

    :param user: Instance of :class: ``User``
    :return: {asset_group: {system_user1, }, asset_group2: {system_user1, system_user2]}
    """
    asset_groups = {}
    user_groups = user.groups.all()
    asset_permissions = set()

    # Get asset permission list of user groups for this user
    for user_group in user_groups:
        asset_permissions |= set(user_group.asset_permissions.all())

    # Get asset groups granted from user groups
    for asset_permission in asset_permissions:
        if not asset_permission.is_valid:
            continue
        for asset_group in asset_permission.asset_groups.all():
            if asset_group in asset_groups:
                asset_groups[asset_group] |= set(asset_permission.system_users.all())
            else:
                setattr(asset_group, 'is_inherit_from_user_group', True)
                asset_groups[asset_group] = set(asset_permission.system_users.all())

    return asset_groups


def get_user_granted_asset_groups(user):
    """Get user granted asset groups all, include direct and inherit from user group

    :param user: Instance of :class: ``User``
    :return: {asset1: {system_user1, system_user2}, asset2: {...}}
    """

    asset_groups_inherit_from_user_groups = get_user_granted_asset_groups_inherit_from_user_groups(user)
    asset_groups_direct = get_user_granted_asset_groups_direct(user)
    asset_groups = asset_groups_inherit_from_user_groups

    # Merge direct granted and inherit from user group
    for asset_group, system_users in asset_groups_direct.items():
        if asset_group in asset_groups:
            asset_groups[asset_group] |= asset_groups_direct[asset_group]
        else:
            asset_groups[asset_group] = asset_groups_direct[asset_group]
    return asset_groups


def get_user_granted_assets_direct(user):
    """Return assets granted of the user directly

     :param user: Instance of :class: ``User``
     :return: {asset1: {system_user1, system_user2}, asset2: {...}}
    """
    assets = {}
    asset_permissions_direct = user.asset_permissions.all()

    for asset_permission in asset_permissions_direct:
        if not asset_permission.is_valid:
            continue
        for asset in asset_permission.get_granted_assets():
            if asset in assets:
                assets[asset] |= set(asset_permission.system_users.all())
            else:
                setattr(asset, 'is_inherit_from_user_groups', False)
                setattr(asset, 'is_inherit_from_user_groups', False)
                assets[asset] = set(asset_permission.system_users.all())

    return assets


def get_user_granted_assets_inherit_from_user_groups(user):
    """Return assets granted of the user inherit from user groups

    :param user: Instance of :class: ``User``
    :return: {asset1: {system_user1, system_user2}, asset2: {...}}
    """
    assets = {}
    user_groups = user.groups.all()

    for user_group in user_groups:
        assets_inherited = get_user_group_granted_assets(user_group)
        for asset in assets_inherited:
            if asset in assets:
                assets[asset] |= assets_inherited[asset]
            else:
                setattr(asset, 'is_inherit_from_user_groups', True)
                assets[asset] = assets_inherited[asset]

    return assets


def get_user_granted_assets(user):
    """Return assets granted of the user inherit from user groups

    :param user: Instance of :class: ``User``
    :return: {asset1: {system_user1, system_user2}, asset2: {...}}
    """
    assets_direct = get_user_granted_assets_direct(user)
    assets_inherited = get_user_granted_assets_inherit_from_user_groups(user)
    assets = assets_inherited

    for asset in assets_direct:
        if asset in assets:
            assets[asset] |= assets_direct[asset]
        else:
            assets[asset] = assets_direct[asset]
    return assets


def get_user_group_asset_permissions(user_group):
    permissions = user_group.asset_permissions.all()
    return permissions


def get_user_asset_permissions(user):
    user_group_permissions = set()
    direct_permissions = set(setattr_bulk(user.asset_permissions.all(), 'inherited', 0))

    for user_group in user.groups.all():
        permissions = get_user_group_asset_permissions(user_group)
        user_group_permissions |= set(permissions)
    user_group_permissions = set(setattr_bulk(user_group_permissions, 'inherited', 1))
    return direct_permissions | user_group_permissions


def get_user_groups_granted_in_asset(asset):
    pass


def get_users_granted_in_asset(asset):
    pass


def get_user_groups_granted_in_asset_group(asset):
    pass


def get_users_granted_in_asset_group(asset):
    pass
