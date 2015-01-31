#coding: utf-8
from connect import PyCrypt, KEY
from jasset.models import Asset, BisGroup, IDC
from django.shortcuts import render_to_response


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