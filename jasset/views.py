# coding:utf-8
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.paginator import Paginator, EmptyPage

from models import IDC, Asset, BisGroup
from juser.models import UserGroup
from connect import PyCrypt, KEY
from jperm.models import Perm

cryptor = PyCrypt(KEY)


def index(request):
    return render_to_response('jasset/jasset.html', )


def jadd_host(request):
    login_types = {'L': 'LDAP', 'S': 'SSH_KEY', 'P': 'PASSWORD', 'M': 'MAP'}
    header_title, path1, path2 = u'添加主机 | Add Host', u'资产管理', u'添加主机'
    groups = []
    eidc = IDC.objects.all()
    egroup = BisGroup.objects.all()
    eusergroup = UserGroup.objects.all()

    if request.method == 'POST':
        j_ip = request.POST.get('j_ip')
        j_idc = request.POST.get('j_idc')
        j_port = request.POST.get('j_port')
        j_type = request.POST.get('j_type')
        j_group = request.POST.getlist('j_group')
        j_active = request.POST.get('j_active')
        j_comment = request.POST.get('j_comment')
        j_idc = IDC.objects.get(name=j_idc)

        for group in j_group:
            c = BisGroup.objects.get(name=group)
            groups.append(c)

        if Asset.objects.filter(ip=str(j_ip)):
            emg = u'该IP已存在!'
            return render_to_response('jasset/host_add.html', locals(), context_instance=RequestContext(request))

        if j_type == 'M':
            j_user = request.POST.get('j_user')
            j_password = cryptor.encrypt(request.POST.get('j_password'))
            j_root = request.POST.get('j_root')
            j_passwd = cryptor.encrypt(request.POST.get('j_passwd'))
            a = Asset(ip=j_ip, port=j_port,
                      login_type=j_type, idc=j_idc,
                      is_active=int(j_active),
                      comment=j_comment,
                      username_common=j_user,
                      password_common=j_password,
                      username_super=j_root,
                      password_super=j_passwd,)
        else:
            a = Asset(ip=j_ip, port=j_port,
                      login_type=j_type, idc=j_idc,
                      is_active=int(j_active),
                      comment=j_comment)
        a.save()
        print 'ok'
        a.bis_group = groups
        a.save()
        smg = u'主机 %s 添加成功' %j_ip
    return render_to_response('jasset/host_add.html', locals(), context_instance=RequestContext(request))


def jlist_host(request):
    header_title, path1, path2 = u'查看主机 | List Host', u'资产管理', u'查看主机'
    login_types = {'L': 'LDAP', 'S': 'SSH_KEY', 'P': 'PASSWORD', 'M': 'MAP'}
    posts = contact_list = Asset.objects.all().order_by('ip')
    print posts
    p = paginator = Paginator(contact_list, 5)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        contacts = paginator.page(page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)

    return render_to_response('jasset/host_list.html', locals(), context_instance=RequestContext(request))

def host_del(request, offset):
    Asset.objects.filter(ip=str(offset)).delete()
    return HttpResponseRedirect('/jasset/host_list/')

def host_edit(request, offset):
    actives = {1: u'激活', 0: u'禁用'}
    login_types = {'L': 'LDAP', 'S': 'SSH_KEY', 'P': 'PASSWORD', 'M': 'MAP'}
    header_title, path1, path2 = u'修改主机 | Edit Host', u'资产管理', u'修改主机'
    groups, e_group = [], []
    eidc = IDC.objects.all()
    egroup = BisGroup.objects.all()
    for g in Asset.objects.get(ip=offset).bis_group.all():
        e_group.append(g)
    post = Asset.objects.get(ip = str(offset))
    if request.method == 'POST':
        j_ip = request.POST.get('j_ip')
        j_idc = request.POST.get('j_idc')
        j_port = request.POST.get('j_port')
        j_type = request.POST.get('j_type')
        j_group = request.POST.getlist('j_group')
        j_active = request.POST.get('j_active')
        j_comment = request.POST.get('j_comment')
        j_idc = IDC.objects.get(name=j_idc)
        for group in j_group:
            c = BisGroup.objects.get(name=group)
            groups.append(c)

        a = Asset.objects.get(ip=str(offset))

        if j_type == 'M':
            j_user = request.POST.get('j_user')
            j_password = cryptor.encrypt(request.POST.get('j_password'))
            j_root = request.POST.get('j_root')
            j_passwd = cryptor.encrypt(request.POST.get('j_passwd'))
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
            a.is_active = j_active
            a.comment = j_comment

        a.save()
        a.bis_group = groups
        a.save()
        smg = u'主机 %s 修改成功' %j_ip
        return HttpResponseRedirect('/jasset/host_list')

    return render_to_response('jasset/host_edit.html', locals(), context_instance=RequestContext(request))


def jlist_ip(request, offset):
    header_title, path1, path2 = u'主机详细信息 | Host Detail.', u'资产管理', u'主机详情'
    print offset
    post = contact_list = Asset.objects.get(ip = str(offset))
    return render_to_response('jasset/jlist_ip.html', locals(), context_instance=RequestContext(request))

def jadd_idc(request):
    header_title, path1, path2 = u'添加IDC | Add IDC', u'资产管理', u'添加IDC'
    if request.method == 'POST':
        j_idc = request.POST.get('j_idc')
        j_comment = request.POST.get('j_comment')
        print j_idc,j_comment

        if IDC.objects.filter(name=j_idc):
            emg = u'该IDC已存在!'
            return render_to_response('jasset/idc_add.html', locals(), context_instance=RequestContext(request))
        else:
            smg = u'IDC:%s添加成功' %j_idc
            IDC.objects.create(name=j_idc, comment=j_comment)

    return render_to_response('jasset/idc_add.html', locals(), context_instance=RequestContext(request))


def jlist_idc(request):
    header_title, path1, path2 = u'查看IDC | List Host', u'资产管理', u'查看IDC'
    posts = IDC.objects.all().order_by('id')
    return render_to_response('jasset/idc_list.html', locals(), context_instance=RequestContext(request))

def idc_del(request, offset):
    IDC.objects.filter(id=offset).delete()
    return HttpResponseRedirect('/jasset/idc_list/')

def jadd_group(request):
    header_title, path1, path2 = u'添加业务组 | Add Group', u'资产管理', u'添加业务组'
    if request.method == 'POST':
        j_group = request.POST.get('j_group')
        j_comment = request.POST.get('j_comment')

        if BisGroup.objects.filter(name=j_group):
            emg = u'该业务组已存在!'
            return render_to_response('jasset/group_add.html', locals(), context_instance=RequestContext(request))
        else:
            smg = u'业务组%s添加成功' %j_group
            BisGroup.objects.create(name=j_group, comment=j_comment)

    return render_to_response('jasset/group_add.html', locals(), context_instance=RequestContext(request))


def jlist_group(request):
    header_title, path1, path2 = u'查看业务组 | Add Group', u'资产管理', u'查看业务组'
    posts = BisGroup.objects.all().order_by('id')
    return render_to_response('jasset/group_list.html', locals(), context_instance=RequestContext(request))

def group_del(request, offset):
    BisGroup.objects.filter(id=offset).delete()
    return HttpResponseRedirect('/jasset/group_list/')

def test(request):
    return render_to_response('jasset/test.html', locals())