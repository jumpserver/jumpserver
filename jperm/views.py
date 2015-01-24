# coding: utf-8

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from juser.models import User, UserGroup
from jasset.models import Asset
from jperm.models import Perm
from django.core.paginator import Paginator, EmptyPage, InvalidPage


def perm_host(request):
    header_title, path1, path2 = u'主机授权 | Perm Host Detail.', u'jperm', u'perm_host'
    users = contact_list = User.objects.all().order_by('id')
    groups = contact_list2 = UserGroup.objects.all().order_by('id')
    p = paginator = Paginator(contact_list, 10)
    p2 = paginator2 = Paginator(contact_list2, 10)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        contacts = paginator.page(page)
        contacts2 = paginator2.page(page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)
        contacts2 = paginator2.page(paginator2.num_pages)
    return render_to_response('jperm/perm_host.html', locals())


def perm_add(request):
    header_title, path1, path2 = u'添加授权 | Add User perm.', u'授权管理', u'添加授权'
    if request.method == 'GET':
        username = request.GET.get('username', None)
        if not username:
            return HttpResponseRedirect('/')

        user = User.objects.get(username=username)
        permed_hosts = []
        for perm in user.perm_set.all():
            permed_hosts.append(perm.asset)

        hosts_all = Asset.objects.all()
        hosts = list(set(hosts_all) - set(permed_hosts))

    else:
        username = request.POST.get('username', None)
        host_ids = request.POST.getlist('host_ids', None)

        user = User.objects.get(username=username)
        for id in host_ids:
            asset = Asset.objects.get(id=id)
            perm = Perm(user=user, asset=asset)
            perm.save()
            msg = u'添加成功'

    return render_to_response('jperm/perm_add.html', locals())


def perm_user_show(request):
    header_title, path1, path2 = u'查看授权用户 | Perm User Detail.', u'授权管理', u'用户详情'
    users = User.objects.all()
    return render_to_response('jperm/perm_user_show.html', locals(),)


def perm_list(request):
    header_title, path1, path2 = u'查看用户授权 | Perm User Detail.', u'授权管理', u'用户详情'
    username = request.GET.get('username', None)
    if not username:
        return HttpResponseRedirect('/')

    user = User.objects.get(username=username)
    hosts = []
    for perm in user.perm_set.all():
        hosts.append(perm.asset)

    return render_to_response('jperm/perm_list.html', locals())
