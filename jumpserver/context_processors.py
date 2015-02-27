
def name_proc(request):
    user_id = request.session.get('user_id')
    role = request.session.get('role')
    return {'user_id': user_id, 'role': role}