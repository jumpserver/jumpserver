from juser.models import User
from jasset.models import Asset
from jumpserver.api import *


def name_proc(request):
    user_id = request.session.get('user_id')
    role_id = request.session.get('role_id')
    # if role_id == 2:
    user_total_num = User.objects.all().count()
    user_active_num = User.objects.filter().count()
    host_total_num = Asset.objects.all().count()
    host_active_num = Asset.objects.filter(is_active=True).count()
    # else:
    #     pass

    request.session.set_expiry(3600)

    info_dic = {'session_user_id': user_id,
                'session_role_id': role_id,
                'user_total_num': user_total_num,
                'user_active_num': user_active_num,
                'host_total_num': host_total_num,
                'host_active_num': host_active_num,
                }

    return info_dic

