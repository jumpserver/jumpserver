#coding: utf-8

import hashlib

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect

from juser.models import User
from connect import PyCrypt, KEY
from jasset.models import Asset, BisGroup, IDC


def md5_crypt(string):
    return hashlib.new("md5", string).hexdigest()


def base(request):
    return render_to_response('base.html')


def skin_config(request):
    return render_to_response('skin_config.html')


def jasset_group_add(name, comment, type):
    if BisGroup.objects.filter(name=name):
        emg = u'该业务组已存在!'
    else:
        BisGroup.objects.create(name=name, comment=comment, type=type)
        smg = u'业务组%s添加成功' %name

def jasset_host_edit(j_ip, j_idc, j_port, j_type, j_group, j_active, j_comment):
    groups = []
    is_active = {u'是': '1', u'否': '2'}
    login_types = {'LDAP': 'L', 'SSH_KEY': 'S', 'PASSWORD': 'P', 'MAP': 'M'}
    for group in j_group:
        c = BisGroup.objects.get(name=group.strip())
        groups.append(c)
    j_type = login_types[j_type]
    j_idc = IDC.objects.get(name=j_idc)
    a = Asset.objects.get(ip=str(j_ip))

    if j_type == 'M':
        a.ip = j_ip
        a.port = j_port
        a.login_type = j_type
        a.idc = j_idc
        a.is_active = j_active
        a.comment = j_comment
        a.username_common = j_user
        a.password_common = j_password
        a.username_super = j_root
        a.password_super = j_passwd
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
