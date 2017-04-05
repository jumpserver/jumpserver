# ~*~ coding: utf-8 ~*~
#
from ops.utils import run_AdHoc


def test_admin_user_connective_manual(asset):
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

