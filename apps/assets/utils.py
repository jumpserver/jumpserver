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
