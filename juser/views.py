# coding: utf-8

from django.shortcuts import render_to_response

from juser.models import Group, User


class AddError(Exception):
    pass


def group_add(request):
    error = ''
    msg = ''
    if request.method == 'POST':
        group_name = request.POST.get('j_group_name', None)
        comment = request.POST.get('j_comment', None)

        try:
            if not group_name:
                error = u'组名不能为空'
                raise AddError

            group = Group.objects.filter(name=group_name)
            if group:
                error = u'组 %s 已存在' % group_name
                assert AddError

            group = Group(name=group_name, comment=comment)
            group.save()
        except AddError:
            pass

        except TypeError:
            error = u'保存用户失败'

        else:
            msg = u'添加用户成功'

    return render_to_response('juser/group_add.html',
                              {'header_title': u'添加属组 | Add Group',
                               'path1': 'juser', 'path2': 'group_add',
                               'error': error, 'msg': msg})


def user_add(request):
    return render_to_response('juser/user_add.html',
                              {'header_title': u'添加用户 | Add User', 'path1': 'juser', 'path2': 'user_add'})





