#coding:utf-8


def name_proc(request):
    name = request.session.get('username')
    admin = request.session.get('admin')
    return {'name': name, 'admin': admin}