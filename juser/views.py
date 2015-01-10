# coding: utf-8
# Author: Guanghongwei
# Email: ibuler@qq.com

import time

from django.shortcuts import render_to_response

from juser.models import UserGroup, User


class AddError(Exception):
    pass


def group_add(request):
    error = ''
    msg = ''
    if request.method == 'POST':
        group_name = request.POST.get('group_name', None)
        comment = request.POST.get('comment', None)

        try:
            if not group_name:
                error = u'组名不能为空'
                raise AddError

            group = UserGroup.objects.filter(name=group_name)
            if group:
                error = u'组 %s 已存在' % group_name
                raise AddError

            group = UserGroup(name=group_name, comment=comment)
            group.save()
        except AddError:
            pass

        except TypeError:
            error = u'保存用户失败'

        else:
            msg = u'添加组 %s 成功' % group_name

    return render_to_response('juser/group_add.html',
                              {'header_title': u'添加属组 | Add Group',
                               'path1': 'juser', 'path2': 'group_add',
                               'error': error, 'msg': msg})


def group_list(request):
    groups = UserGroup.objects.all()
    return render_to_response('juser/group_list.html',
                              {'header_title': u'查看属组 | Add Group',
                               'path1': 'juser', 'path2': 'group_add',
                               'groups': groups})


def user_list(request):
    pass


def db_add_user(**kwargs):
    groups_post = kwargs.pop('groups')
    user = User(**kwargs)
    group_select = []
    for group_id in groups_post:
        group = UserGroup.objects.filter(id=group_id)
        group_select.extend(group)
    user.save()
    user.user_group = group_select


def db_del_user(username):
    user = User.objects.get(username=username)
    user.delete()


def user_add(request):
    error = ''
    msg = ''

    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    all_group = UserGroup.objects.all()
    if request.method == 'POST':
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        name = request.POST.get('name', None)
        email = request.POST.get('email', '')
        groups = request.POST.getlist('groups', None)
        role = request.POST.get('role', None)
        ssh_pwd = request.POST.get('ssh_pwd', None)
        ssh_key_pwd1 = request.POST.get('ssh_key_pwd1', None)
        is_active = request.POST.get('is_active', '1')

        try:
            if None in [username, password, ssh_key_pwd1, name, groups, role, is_active]:
                error = u'带*内容不能为空'
                raise AddError
            user = User.objects.filter(username=username)
            if user:
                error = u'用户 %s 已存在' % username
                raise AddError

        except AddError:
            pass
        else:
            time_now = time.time()
            db_add_user(username=username, password=password, name=name, email=email,
                        groups=groups, role=role, ssh_pwd=ssh_pwd, ssh_key_pwd1=ssh_key_pwd1,
                        is_active=is_active, date_joined=time_now)
            msg = u'添加用户成功'
    return render_to_response('juser/user_add.html',
                              {'header_title': u'添加用户 | Add User',
                               'path1': 'juser', 'path2': 'user_add',
                               'roles': user_role, 'all_group': all_group,
                               'error': error, 'msg': msg})







