# coding: utf-8

from django.shortcuts import render_to_response


def group_add(request):
    return render_to_response('juser/group_add.html',
                              {'header_title': u'添加属组 | Add Group', 'path1': 'juser', 'path2': 'group_add'})


def user_add(request):
    return render_to_response('juser/user_add.html',
                              {'header_title': u'添加用户 | Add User', 'path1': 'juser', 'path2': 'user_add'})





