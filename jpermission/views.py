# coding: utf-8

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from juser.models import User
from jasset.models import Asset


def perm_user_list(request):
    header_title, path1, path2 = u'查看授权用户 | Perm User Detail.', u'授权管理', u'用户详情'
    users = User.objects.all()
    return render_to_response('jperm/perm_user_list.html', locals(),)


def perm_add(request):
    header_title, path1, path2 = u'添加授权 | Add User perm.', u'授权管理', u'添加授权'
    username = request.GET.get('username', None)
    if not username:
        return HttpResponseRedirect('/')

    user = User.objects.get(username=username)
    permed_hosts = []
    for perm in user.permission_set.all():
        permed_hosts.append(perm.asset)

    hosts_all = Asset.objects.all()
    hosts = list(set(hosts_all) - set(permed_hosts))

    return render_to_response('jperm/perm_add.html', locals())