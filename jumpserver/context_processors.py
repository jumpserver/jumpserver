from juser.models import User


def name_proc(request):
    user_id = request.session.get('user_id')
    role = request.session.get('role_id')
    user_total_num = User.objects.all().count()
    user_active_num = User.objects.filter(is_active=True).count()

    return {'session_user_id': user_id, 'session_role_id': role,
            'user_total_num': user_total_num, 'user_active_num': user_active_num}

