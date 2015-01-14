# coding:utf-8
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.paginator import Paginator, EmptyPage

from models import IDC, Asset, BisGroup
from models import IDC, Asset, UserGroup
from connect import PyCrypt, KEY


def index(request):
    return render_to_response('jasset/jasset.html', )


def jadd_host(request):
    header_title, path1, path2 = '添加主机 | Add Host', '资产管理', '添加主机'
    groups = []
    cryptor = PyCrypt(KEY)
    eidc = IDC.objects.all()
    egroup = BisGroup.objects.all()
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

        j_idc = IDC.objects.get(name=j_idc)
        for group in j_group:
            c = BisGroup.objects.get(name=group)
            c = UserGroup.objects.get(name=group)
            groups.append(c)

        if Asset.objects.filter(ip=str(j_ip)):
            emg = u'该IP已存在!'
            return render_to_response('jasset/jadd.html', locals(), context_instance=RequestContext(request))

        if j_type == 'MAP':
            j_user = request.POST.get('j_user')
            j_password = cryptor.encrypt(request.POST.get('j_password'))
            j_root = request.POST.get('j_root')
            j_passwd = cryptor.encrypt(request.POST.get('j_passwd'))
            a = Asset(ip=j_ip,
                      port=j_port,
                      login_type=j_type,
                      idc=j_idc,
                      is_active=int(j_active),
                      comment=j_comment,
                      username_common=j_user,
                      password_common=j_password,
                      username_super=j_root,
                      password_super=j_passwd,)
        else:
            a = Asset(ip=j_ip,
                      port=j_port,
                      login_type=j_type,
                      idc=j_idc,
                      is_active=int(j_active),
                      comment=j_comment)
        a.save()
        a.bis_group = groups
        a.save()

    return render_to_response('jasset/jadd.html', locals(), context_instance=RequestContext(request))


def jlist_host(request):
    header_title, path1, path2 = '查看主机 | List Host', '资产管理', '查看主机'
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

    return render_to_response('jasset/jlist.html', locals(), context_instance=RequestContext(request))

def jlist_ip(request, offset):
    header_title, path1, path2 = '主机详细信息 | Host Detail.', '资产管理', '主机详情'
    print offset
    post = contact_list = Asset.objects.get(ip = str(offset))
    return render_to_response('jasset/jlist_ip.html', locals(), context_instance=RequestContext(request))

def jadd_idc(request):
    header_title, path1, path2 = '添加IDC | Add IDC', '资产管理', '添加IDC'
    if request.method == 'POST':
        j_idc = request.POST.get('j_idc')
        j_comment = request.POST.get('j_comment')
        print j_idc,j_comment

        if IDC.objects.filter(name=j_idc):
            emg = u'该IDC已存在!'
            return render_to_response('jasset/jadd_idc.html',
                                      {'emg': emg, 'j_idc': j_idc, 'j_comment': j_comment,},
                                      context_instance=RequestContext(request))
        else:
            IDC.objects.create(name=j_idc, comment=j_comment)

    return render_to_response('jasset/jadd_idc.html', locals(), context_instance=RequestContext(request))


def jlist_idc(request):
    header_title, path1, path2 = '查看IDC | List Host', '资产管理', '查看IDC'
    posts = IDC.objects.all().order_by('id')
    return render_to_response('jasset/jlist_idc.html', locals(), context_instance=RequestContext(request))


def jadd_group(request):
    header_title, path1, path2 = '添加业务组 | Add Group', '资产管理', '添加业务组'
    if request.method == 'POST':
        j_group = request.POST.get('j_group')
        j_comment = request.POST.get('j_comment')

        if BisGroup.objects.filter(name=j_group):
            emg = u'该业务组已存在!'
            return render_to_response('jasset/jadd_group.html', locals(), context_instance=RequestContext(request))
        else:
            BisGroup.objects.create(name=j_group, comment=j_comment)

    return render_to_response('jasset/jadd_group.html', locals(), context_instance=RequestContext(request))


def jlist_group(request):
    header_title, path1, path2 = '添加业务组 | Add Group', '资产管理', '查看业务组'
    posts = BisGroup.objects.all().order_by('id')
    return render_to_response('jasset/jlist_group.html', locals(), context_instance=RequestContext(request))
