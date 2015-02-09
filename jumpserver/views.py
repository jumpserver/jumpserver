#coding: utf-8

import hashlib

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, InvalidPage

from juser.models import User
from jasset.models import Asset, BisGroup, IDC


def md5_crypt(string):
    return hashlib.new("md5", string).hexdigest()


def base(request):
    return render_to_response('base.html')


def skin_config(request):
    return render_to_response('skin_config.html')


def jasset_group_add(name, comment, jtype):
    if BisGroup.objects.filter(name=name):
        emg = u'该业务组已存在!'
    else:
        BisGroup.objects.create(name=name, comment=comment, type=jtype)
        smg = u'业务组%s添加成功' %name


def jasset_host_edit(j_id, j_ip, j_idc, j_port, j_type, j_group, j_active, j_comment):
    groups = []
    is_active = {u'是': '1', u'否': '2'}
    login_types = {'LDAP': 'L', 'SSH_KEY': 'S', 'PASSWORD': 'P', 'MAP': 'M'}
    for group in j_group[0].split():
        print group.strip()
        c = BisGroup.objects.get(name=group.strip())
        groups.append(c)
    j_type = login_types[j_type]
    print j_type
    j_idc = IDC.objects.get(name=j_idc)
    print j_idc
    print
    a = Asset.objects.get(id=j_id)
    if j_type == 'M':
        a.ip = j_ip
        a.port = j_port
        a.login_type = j_type
        a.idc = j_idc
        a.is_active = j_active
        a.comment = j_comment
        a.username = j_user
        a.password = j_password
    else:
        a.ip = j_ip
        a.port = j_port
        a.idc = j_idc
        a.login_type = j_type
        a.is_active = is_active[j_active]
        a.comment = j_comment
    a.save()
    a.bis_group = groups
    a.save()


def pages(posts, r):
    contact_list = posts
    p = paginator = Paginator(contact_list, 10)
    try:
        page = int(r.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        contacts = paginator.page(page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)

    return contact_list, p, contacts


def login(request):
    """登录界面"""
    if request.session.get('username'):
        return HttpResponseRedirect('/')
    if request.method == 'GET':
        return render_to_response('login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = User.objects.filter(username=username)
        if user:
            user = user[0]
            if md5_crypt(password) == user.password:
                request.session['username'] = username
                if user.role == 'SU':
                    request.session['role'] = 2
                elif user.role == 'GA':
                    request.session['role'] = 1
                else:
                    request.session['role'] = 0
                return HttpResponseRedirect('/')
            else:
                error = '密码错误，请重新输入。'
        else:
            error = '用户不存在。'
    return render_to_response('login.html', {'error': error})


def logout(request):
    request.session.delete()
    return HttpResponseRedirect('/login/')

