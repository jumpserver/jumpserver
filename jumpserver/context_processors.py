from juser.models import User
from jasset.models import Asset
from jumpserver.api import *


def name_proc(request):
    user_id = request.user.id
    role_id = {'SU': 2, 'GA': 1, 'CU': 0}.get(request.user.role, 0)
    # role_id = 'SU'
    user_total_num = User.objects.all().count()
    user_active_num = User.objects.filter().count()
    host_total_num = Asset.objects.all().count()
    host_active_num = Asset.objects.filter(is_active=True).count()
    request.session.set_expiry(3600)

    info_dic = {'session_user_id': user_id,
                'session_role_id': role_id,
                'user_total_num': user_total_num,
                'user_active_num': user_active_num,
                'host_total_num': host_total_num,
                'host_active_num': host_active_num,
                }

    return info_dic

