from juser.models import User
from jasset.models import Asset
from jumpserver.api import *
from jperm.models import Apply


def name_proc(request):
    user_id = request.session.get('user_id')
    role_id = request.session.get('role_id')
    if role_id == 2:
        user_total_num = User.objects.all().count()
        user_active_num = User.objects.filter().count()
        host_total_num = Asset.objects.all().count()
        host_active_num = Asset.objects.filter(is_active=True).count()
    else:
        user, dept = get_session_user_dept(request)
        user_total_num = dept.user_set.all().count()
        user_active_num = dept.user_set.filter(is_active=True).count()
        host_total_num = dept.asset_set.all().count()
        host_active_num = dept.asset_set.all().filter(is_active=True).count()

    username = User.objects.get(id=user_id).name
    apply_info = Apply.objects.filter(admin=username, status=0, read=0)
    request.session.set_expiry(3600)

    info_dic = {'session_user_id': user_id,
                'session_role_id': role_id,
                'user_total_num': user_total_num,
                'user_active_num': user_active_num,
                'host_total_num': host_total_num,
                'host_active_num': host_active_num,
                'apply_info': apply_info}

    return info_dic

