# ~*~ coding: utf-8 ~*~
#
from .models import Asset


def test_admin_user_connective_manual(asset):
    from ops.utils import run_AdHoc
    if not isinstance(asset, list):
        asset = [asset]
    task_tuple = (
        ('ping', ''),
    )
    summary, _ = run_AdHoc(task_tuple, asset, record=False)
    if len(summary['failed']) != 0:
        return False
    else:
        return True


def get_assets_by_id_list(id_list):
    return Asset.objects.filter(id__in=id_list)


def get_assets_by_hostname_list(hostname_list):
    return Asset.objects.filter(hostname__in=hostname_list)


def get_asset_admin_user(user, asset):
    if user.is_superuser:
        return asset.admin_user
    else:
        msg = "{} have no permission for admin user".format(user.username)
        raise PermissionError(msg)


def get_asset_system_user(user, asset, system_user_name):
    from perms.utils import get_user_granted_assets
    assets = get_user_granted_assets(user)
    system_users = {system_user.name: system_user for system_user in assets.get(asset)}

    if system_user_name in system_users:
        return system_users[system_user_name]
    else:
        msg = "{} have no permission for {}".format(user.name, system_user_name)
        raise PermissionError(msg)


def get_assets_with_admin_by_hostname_list(hostname_list):
    assets = Asset.objects.filter(hostname__in=hostname_list)
    return [(asset, asset.admin_user) for asset in assets]
