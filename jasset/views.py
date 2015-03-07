# coding:utf-8

from django.db.models import Q
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response

from models import IDC, Asset, BisGroup
from juser.models import UserGroup
from connect import PyCrypt, KEY
from jlog.models import Log
from jumpserver.views import jasset_group_add, jasset_host_edit, pages
from jumpserver.api import asset_perm_api

cryptor = PyCrypt(KEY)


def index(request):
    return render_to_response('jasset/jasset.html', )


def f_add_host(ip, port, idc, jtype, group, active, comment, username='', password=''):
    groups = []
    idc = IDC.objects.get(name=idc)
    if type == 'M':
        a = Asset(ip=ip, port=port,
                  login_type=jtype, idc=idc,
                  is_active=int(active),
                  comment=comment,
                  username=username,
                  password=password)
    else:
        a = Asset(ip=ip, port=port,
                  login_type=jtype, idc=idc,
                  is_active=int(active),
                  comment=comment)
    a.save()

    jasset_group_add(ip, ip, 'P')
    all_group = BisGroup.objects.get(name='ALL')
    private_group = BisGroup.objects.get(name=ip.strip())
    for g in group:
        c = BisGroup.objects.get(name=g)
        groups.append(c)
    groups.extend([all_group, private_group])

    a.bis_group = groups
    a.save()


def add_host(request):
    login_types = {'L': 'LDAP', 'S': 'SSH_KEY', 'P': 'PASSWORD', 'M': 'MAP'}
    header_title, path1, path2 = u'添加主机', u'资产管理', u'添加主机'
    eidc = IDC.objects.all()
    egroup = BisGroup.objects.filter(type='A')
    eusergroup = UserGroup.objects.all()

    if request.method == 'POST':
        j_ip = request.POST.get('j_ip')
        j_idc = request.POST.get('j_idc')
        j_port = request.POST.get('j_port')
        j_type = request.POST.get('j_type')
        j_group = request.POST.getlist('j_group')
        j_active = request.POST.get('j_active')
        j_comment = request.POST.get('j_comment')

        if Asset.objects.filter(ip=str(j_ip)):
            emg = u'该IP %s 已存在!' % j_ip
            return render_to_response('jasset/host_add.html', locals(), context_instance=RequestContext(request))

        if j_type == 'M':
            j_user = request.POST.get('j_user')
            j_password = cryptor.encrypt(request.POST.get('j_password'))
            f_add_host(j_ip, j_port, j_idc, j_type, j_group, j_active, j_comment, j_user, j_password)
        else:
            f_add_host(j_ip, j_port, j_idc, j_type, j_group, j_active, j_comment)
        smg = u'主机 %s 添加成功' % j_ip

    return render_to_response('jasset/host_add.html', locals(), context_instance=RequestContext(request))


def add_host_multi(request):
    header_title, path1, path2 = u'批量添加主机', u'资产管理', u'批量添加主机'
    login_types = {'LDAP': 'L', 'SSH_KEY': 'S', 'PASSWORD': 'P', 'MAP': 'M'}
    j_group = []
    if request.method == 'POST':
        multi_hosts = request.POST.get('j_multi').split('\n')
        for host in multi_hosts:
            if host == '':
                break
            j_ip, j_port, j_type, j_idc, j_groups, j_active, j_comment = host.split()
            j_type = login_types[j_type]
            j_groups = j_groups.split(',')
            for group in j_groups:
                g = group.strip('[]').encode('utf-8').strip()
                j_group.append(g)

            if Asset.objects.filter(ip=str(j_ip)):
                emg = u'该IP %s 已存在!' % j_ip
                return render_to_response('jasset/host_add_multi.html', locals(),
                                          context_instance=RequestContext(request))

            if j_type == 'M':
                j_user = request.POST.get('j_user')
                j_password = cryptor.encrypt(request.POST.get('j_password'))
                f_add_host(j_ip, j_port, j_idc, j_type, j_group, j_active, j_comment, j_user, j_password)
            else:
                f_add_host(j_ip, j_port, j_idc, j_type, j_group, j_active, j_comment)

        smg = u'批量添加添加成功'
        return HttpResponseRedirect('/jasset/host_list/')

    return render_to_response('jasset/host_add_multi.html', locals(), context_instance=RequestContext(request))


def batch_host_edit(request):
    if request.method == 'POST':
        len_table = request.POST.get('len_table')
        for i in range(int(len_table)):
            j_id = "editable[" + str(i) + "][j_id]"
            j_ip = "editable[" + str(i) + "][j_ip]"
            j_port = "editable[" + str(i) + "][j_port]"
            j_idc = "editable[" + str(i) + "][j_idc]"
            j_type = "editable[" + str(i) + "][j_type]"
            j_group = "editable[" + str(i) + "][j_group]"
            j_active = "editable[" + str(i) + "][j_active]"
            j_comment = "editable[" + str(i) + "][j_comment]"

            j_id = request.POST.get(j_id).strip()
            j_ip = request.POST.get(j_ip).strip()
            j_port = request.POST.get(j_port).strip()
            j_idc = request.POST.get(j_idc).strip()
            j_type = request.POST.get(j_type).strip()
            j_group = request.POST.getlist(j_group)
            j_active = request.POST.get(j_active).strip()
            j_comment = request.POST.get(j_comment).strip()

            jasset_host_edit(j_id, j_ip, j_idc, j_port, j_type, j_group, j_active, j_comment)

        return render_to_response('jasset/host_list.html')


def list_host(request):
    header_title, path1, path2 = u'查看主机', u'资产管理', u'查看主机'
    login_types = {'L': 'LDAP', 'S': 'SSH_KEY', 'P': 'PASSWORD', 'M': 'MAP'}
    posts = Asset.objects.all().order_by('ip')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    return render_to_response('jasset/host_list.html', locals(), context_instance=RequestContext(request))


def host_del(request, offset):
    if offset == 'multi':
        len_list = request.POST.get("len_list")
        for i in range(int(len_list)):
            key = "id_list[" + str(i) + "]"
            jid = request.POST.get(key)
            a = Asset.objects.get(id=jid).ip
            Asset.objects.filter(id=jid).delete()
            BisGroup.objects.filter(name=a).delete()
    else:
        jid = int(offset)
        a = Asset.objects.get(id=jid).ip
        BisGroup.objects.filter(name=a).delete()
        Asset.objects.filter(id=jid).delete()
    return HttpResponseRedirect('/jasset/host_list/')


def host_edit(request):
    actives = {1: u'激活', 0: u'禁用'}
    login_types = {'L': 'LDAP', 'S': 'SSH_KEY', 'P': 'PASSWORD', 'M': 'MAP'}
    header_title, path1, path2 = u'修改主机', u'资产管理', u'修改主机'
    groups, e_group = [], []
    eidc = IDC.objects.all()
    egroup = BisGroup.objects.filter(type='A')
    offset = request.GET.get('id')
    for g in Asset.objects.get(id=int(offset)).bis_group.all():
        e_group.append(g)
    post = Asset.objects.get(id=int(offset))
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

        a = Asset.objects.get(id=int(offset))
        if j_type == 'M':
            j_user = request.POST.get('j_user')
            j_password = cryptor.encrypt(request.POST.get('j_password'))
            a.ip = j_ip
            a.port = j_port
            a.login_type = j_type
            a.idc = j_idc
            a.is_active = int(j_active)
            a.comment = j_comment
            a.username = j_user
            a.password = j_password
        else:
            a.ip = j_ip
            a.port = j_port
            a.idc = j_idc
            a.login_type = j_type
            a.is_active = int(j_active)
            a.comment = j_comment

        a.save()
        a.bis_group = groups
        a.save()
        smg = u'主机 %s 修改成功' % j_ip
        return HttpResponseRedirect('/jasset/host_list')

    return render_to_response('jasset/host_edit.html', locals(), context_instance=RequestContext(request))


def jlist_ip(request, offset):
    header_title, path1, path2 = u'主机详细信息', u'资产管理', u'主机详情'
    login_types = {'L': 'LDAP', 'S': 'SSH_KEY', 'P': 'PASSWORD', 'M': 'MAP'}
    post = contact_list = Asset.objects.get(ip=str(offset))
    log = Log.objects.filter(host=str(offset))
    user_permed_list = asset_perm_api(Asset.objects.get(ip=str(offset)))
    return render_to_response('jasset/jlist_ip.html', locals(), context_instance=RequestContext(request))


def add_idc(request):
    header_title, path1, path2 = u'添加IDC', u'资产管理', u'添加IDC'
    if request.method == 'POST':
        j_idc = request.POST.get('j_idc')
        j_comment = request.POST.get('j_comment')
        if IDC.objects.filter(name=j_idc):
            emg = u'该IDC已存在!'
            return render_to_response('jasset/idc_add.html', locals(), context_instance=RequestContext(request))
        else:
            smg = u'IDC:%s添加成功' % j_idc
            IDC.objects.create(name=j_idc, comment=j_comment)

    return render_to_response('jasset/idc_add.html', locals(), context_instance=RequestContext(request))


def list_idc(request):
    header_title, path1, path2 = u'查看IDC', u'资产管理', u'查看IDC'
    posts = IDC.objects.all().order_by('id')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
    return render_to_response('jasset/idc_list.html', locals(), context_instance=RequestContext(request))


def del_idc(request, offset):
    IDC.objects.filter(id=offset).delete()
    return HttpResponseRedirect('/jasset/idc_list/')


def add_group(request):
    header_title, path1, path2 = u'添加主机组', u'资产管理', u'添加主机组'
    posts = Asset.objects.all()
    if request.method == 'POST':
        j_group = request.POST.get('j_group')
        j_hosts = request.POST.getlist('j_hosts')
        j_comment = request.POST.get('j_comment')

        if BisGroup.objects.filter(name=j_group):
            emg = u'该主机组已存在!'
            return render_to_response('jasset/group_add.html', locals(), context_instance=RequestContext(request))
        else:
            BisGroup.objects.create(name=j_group, comment=j_comment, type='A')
            group = BisGroup.objects.get(name=j_group)
            for host in j_hosts:
                g = Asset.objects.get(id=host)
                group.asset_set.add(g)
            smg = u'主机组%s添加成功' % j_group

    return render_to_response('jasset/group_add.html', locals(), context_instance=RequestContext(request))


def list_group(request):
    header_title, path1, path2 = u'查看主机组', u'资产管理', u'查看主机组'
    posts = BisGroup.objects.filter(type='A').order_by('id')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    return render_to_response('jasset/group_list.html', locals(), context_instance=RequestContext(request))


def edit_group(request):
    header_title, path1, path2 = u'编辑主机组', u'资产管理', u'编辑主机组'
    group_id = request.GET.get('id')
    group = BisGroup.objects.get(id=group_id)
    all = Asset.objects.all()
    eposts = contact_list = Asset.objects.filter(bis_group=group).order_by('ip')
    posts = [g for g in all if g not in eposts]
    if request.method == 'POST':
        j_group = request.POST.get('j_group')
        j_hosts = request.POST.getlist('j_hosts')
        j_comment = request.POST.get('j_comment')

        group.asset_set.clear()
        for host in j_hosts:
            g = Asset.objects.get(id=host)
            group.asset_set.add(g)
        BisGroup.objects.filter(id=group_id).update(name=j_group, comment=j_comment)
        smg = u'主机组%s修改成功' % j_group
        return HttpResponseRedirect('/jasset/group_detail/?id=%s' % group_id)

    return render_to_response('jasset/group_add.html', locals(), context_instance=RequestContext(request))


def detail_group(request):
    header_title, path1, path2 = u'主机组详情', u'资产管理', u'主机组详情'
    login_types = {'L': 'LDAP', 'S': 'SSH_KEY', 'P': 'PASSWORD', 'M': 'MAP'}
    group_id = request.GET.get('id')
    group_name = BisGroup.objects.get(id=group_id).name
    b = BisGroup.objects.get(id=group_id)
    posts = Asset.objects.filter(bis_group=b).order_by('ip')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    return render_to_response('jasset/group_detail.html', locals(), context_instance=RequestContext(request))


def detail_idc(request):
    header_title, path1, path2 = u'IDC详情', u'资产管理', u'IDC详情'
    login_types = {'L': 'LDAP', 'S': 'SSH_KEY', 'P': 'PASSWORD', 'M': 'MAP'}
    idc_id = request.GET.get('id')
    idc_name = IDC.objects.get(id=idc_id).name
    b = IDC.objects.get(id=idc_id)
    posts = Asset.objects.filter(idc=b).order_by('ip')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    return render_to_response('jasset/idc_detail.html', locals(), context_instance=RequestContext(request))


def group_del_host(request, offset):
    if request.method == 'POST':
        group_name = request.POST.get('group_name')
        if offset == 'group':
            group = BisGroup.objects.get(name=group_name)
        elif offset == 'idc':
            group = IDC.objects.get(name=group_name)
        len_list = request.POST.get("len_list")
        for i in range(int(len_list)):
            key = "id_list[" + str(i) + "]"
            jid = request.POST.get(key)
            g = Asset.objects.get(id=jid)
            if offset == 'group':
                group.asset_set.remove(g)
            elif offset == 'idc':
                Asset.objects.filter(id=jid).delete()
                BisGroup.objects.filter(name=g.ip).delete()

        return HttpResponseRedirect('/jasset/%s_detail/?id=%s' % (offset, group.id))


def group_del(request, offset):
    BisGroup.objects.filter(id=offset).delete()
    return HttpResponseRedirect('/jasset/group_list/')


def host_search(request):
    keyword = request.GET.get('keyword')
    login_types = {'L': 'LDAP', 'S': 'SSH_KEY', 'P': 'PASSWORD', 'M': 'MAP'}
    posts = Asset.objects.filter(Q(ip__contains=keyword) | Q(idc__name__contains=keyword) |
                                 Q(bis_group__name__contains=keyword) | Q(
        comment__contains=keyword)).distinct().order_by('ip')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    return render_to_response('jasset/host_search.html', locals(), context_instance=RequestContext(request))


def test(request):
    return render_to_response('jasset/test.html', locals())
