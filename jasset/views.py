# coding:utf-8
import datetime
from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from models import IDC, Asset, UserGroup
from connect import PyCrypt, KEY


def index(request):
    return render_to_response('jasset/jasset.html', )


def jadd(request):
    global j_passwd
    groups = []
    cryptor = PyCrypt(KEY)
    eidc = IDC.objects.all()
    egroup = UserGroup.objects.all()
    is_actived = {'active': 1, 'no_active': 0}
    login_typed = {'LDAP': 'L', 'SSH_KEY': 'S', 'PASSWORD': 'P', 'MAP': 'M'}

    if request.method == 'POST':
        j_ip = request.POST.get('j_ip')
        j_idc = request.POST.get('j_idc')
        j_port = request.POST.get('j_port')
        j_type = request.POST.get('j_type')
        j_group = request.POST.getlist('j_group')
        j_active = request.POST.get('j_active')
        j_comment = request.POST.get('j_comment')
        if j_type == 'MAP':
            j_user = request.POST.get('j_user')
            j_password = cryptor.encrypt(request.POST.get('j_password'))
            j_root = request.POST.get('j_root')
            j_passwd = cryptor.encrypt(request.POST.get('j_passwd'))

        j_idc = IDC.objects.get(name=j_idc)
        for group in j_group:
            c = UserGroup.objects.get(name=group)
            groups.append(c)

        if Asset.objects.filter(ip=str(j_ip)):
            emg = u'该IP已存在!'
            return render_to_response('jasset/jadd.html', {'emg': emg, 'j_ip': j_ip})

        elif j_type == 'MAP':
            a = Asset(ip=j_ip,
                      port=j_port,
                      login_type=login_typed[j_type],
                      idc=j_idc,
                      is_active=int(is_actived[j_active]),
                      comment=j_comment,
                      username_common=j_user,
                      password_common=j_password,
                      username_super=j_root,
                      password_super=j_passwd,)
        else:
            a = Asset(ip=j_ip,
                      port=j_port,
                      login_type=login_typed[j_type],
                      idc=j_idc,
                      is_active=int(is_actived[j_active]),
                      comment=j_comment)
        a.save()
        a.group = groups
        a.save()

    return render_to_response('jasset/jadd.html',
                              {'header_title': u'添加主机 | Add Host',
                               'path1': '资产管理',
                               'path2': '添加主机',
                               'eidc': eidc,
                               'egroup': egroup, }
                              )


def jlist(request):
    posts = contact_list = Asset.objects.all().order_by('ip')
    print posts
    paginator = Paginator(contact_list, 5)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        contacts = paginator.page(page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)

    return render_to_response('jasset/jlist.html',
                              {"contacts": contacts,
                               'p': paginator,
                               'posts': posts,
                               'header_title': u'查看主机 | List Host',
                               'path1': '资产管理',
                               'path2': '查看主机', },
                              context_instance=RequestContext(request))


def jadd_idc(request):
    pass


def jlist_idc(request):
    pass