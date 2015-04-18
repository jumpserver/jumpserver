# coding:utf-8

import ast

from django.db.models import Q
from django.template import RequestContext
from django.shortcuts import render_to_response

from jasset.models import IDC, Asset, BisGroup, AssetAlias
from jperm.models import Perm, SudoPerm
from jumpserver.api import *

cryptor = PyCrypt(KEY)


class RaiseError(Exception):
    pass


def my_render(template, data, request):
    return render_to_response(template, data, context_instance=RequestContext(request))


def httperror(request, emg):
    message = emg
    return render_to_response('error.html', locals(), context_instance=RequestContext(request))


def get_host_groups(groups):
    """ 获取主机所属的组类 """
    ret = []
    for group_id in groups:
        group = BisGroup.objects.filter(id=group_id)
        if group:
            group = group[0]
            ret.append(group)
    return ret


def get_host_depts(depts):
    """ 获取主机所属的部门类 """
    ret = []
    for dept_id in depts:
        dept = DEPT.objects.filter(id=dept_id)
        if dept:
            dept = dept[0]
            ret.append(dept)
    return ret


def db_host_insert(host_info, username='', password=''):
    """ 添加主机时数据库操作函数 """
    ip, port, idc, jtype, group, dept, active, comment = host_info
    idc = IDC.objects.filter(id=idc)
    if idc:
        idc = idc[0]
    if jtype == 'M':
        password = cryptor.encrypt(password)
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

    all_group = BisGroup.objects.get(name='ALL')
    groups = get_host_groups(group)
    groups.append(all_group)

    depts = get_host_depts(dept)

    a.bis_group = groups
    a.dept = depts
    a.save()


def db_host_update(host_info, username='', password=''):
    """ 修改主机时数据库操作函数 """
    ip, port, idc, jtype, group, dept, active, comment, host = host_info
    idc = IDC.objects.filter(id=idc)
    if idc:
        idc = idc[0]
    groups = get_host_groups(group)
    depts = get_host_depts(dept)
    host.ip = ip
    host.port = port
    host.login_type = jtype
    host.idc = idc
    host.is_active = int(active)
    host.comment = comment

    if jtype == 'M':
        if password != host.password:
            password = cryptor.encrypt(password)
        host.password = password
        host.username = username
        host.password = password
    host.save()
    host.bis_group = groups
    host.dept = depts
    host.save()


def batch_host_edit(host_info, j_user='', j_password=''):
    """ 批量修改主机函数 """
    j_id, j_ip, j_idc, j_port, j_type, j_group, j_dept, j_active, j_comment = host_info
    groups, depts = [], []
    is_active = {u'是': '1', u'否': '2'}
    login_types = {'LDAP': 'L', 'MAP': 'M'}
    for group in j_group[0].split():
        c = BisGroup.objects.get(name=group.strip())
        groups.append(c)
    for d in j_dept[0].split():
        p = DEPT.objects.get(name=d.strip())
        depts.append(p)
    j_type = login_types[j_type]
    j_idc = IDC.objects.get(name=j_idc)
    a = Asset.objects.get(id=j_id)
    if j_type == 'M':
        if a.password != j_password:
            j_password = cryptor.decrypt(j_password)
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
    a.dept = depts
    a.save()


def db_host_delete(request, host_id):
    """ 删除主机操作 """
    if is_group_admin(request) and not validate(request, asset=[host_id]):
        return httperror(request, '删除失败, 您无权删除!')

    asset = Asset.objects.filter(id=host_id)
    if asset:
        asset.delete()
    else:
        return httperror(request, '删除失败, 没有此主机!')


def db_idc_delete(request, idc_id):
    """ 删除IDC操作 """
    if idc_id == 1:
        return httperror(request, '删除失败, 默认IDC不能删除!')

    default_idc = IDC.objects.get(id=1)

    idc = IDC.objects.filter(id=idc_id)
    if idc:
        idc_class = idc.first()
        idc_class.asset_set.update(idc=default_idc)
        idc.delete()
    else:
        return httperror(request, '删除失败, 没有这个IDC!')


@require_admin
def host_add(request):
    """ 添加主机 """
    header_title, path1, path2 = u'添加主机', u'资产管理', u'添加主机'
    login_types = {'L': 'LDAP', 'M': 'MAP'}
    eidc = IDC.objects.exclude(name='ALL')
    if is_super_user(request):
        edept = DEPT.objects.all()
        egroup = BisGroup.objects.exclude(name='ALL')
    elif is_group_admin(request):
        dept = get_session_user_info(request)[5]
        egroup = dept.bisgroup_set.all()

    if request.method == 'POST':
        j_ip = request.POST.get('j_ip')
        j_idc = request.POST.get('j_idc')
        j_port = request.POST.get('j_port')
        j_type = request.POST.get('j_type')
        j_group = request.POST.getlist('j_group')
        j_active = request.POST.get('j_active')
        j_comment = request.POST.get('j_comment')
        j_dept = request.POST.getlist('j_dept')

        host_info = [j_ip, j_port, j_idc, j_type, j_group, j_dept, j_active, j_comment]
        if is_group_admin(request) and not verify(request, asset_group=j_group, edept=j_dept):
            return httperror(request, u'添加失败,您无权操作!')

        if Asset.objects.filter(ip=str(j_ip)):
            emg = u'该IP %s 已存在!' % j_ip
            return my_render('jasset/host_add.html', locals(), request)
        if j_type == 'M':
            j_user = request.POST.get('j_user')
            j_password = request.POST.get('j_password', '')
            db_host_insert(host_info, j_user, j_password)
        else:
            db_host_insert(host_info)
        smg = u'主机 %s 添加成功' % j_ip

    return my_render('jasset/host_add.html', locals(), request)


@require_admin
def host_add_batch(request):
    """ 批量添加主机 """
    header_title, path1, path2 = u'批量添加主机', u'资产管理', u'批量添加主机'
    login_types = {'LDAP': 'L', 'MAP': 'M'}
    active_types = {'激活': 1, '禁用': 0}
    dept_id = get_user_dept(request)
    if request.method == 'POST':
        multi_hosts = request.POST.get('j_multi').split('\n')
        for host in multi_hosts:
            if host == '':
                break
            j_ip, j_port, j_type, j_idc, j_groups, j_depts, j_active, j_comment = host.split()
            j_type = login_types[j_type]
            j_active = active_types[str(j_active)]
            j_group = ast.literal_eval(j_groups)
            j_dept = ast.literal_eval(j_depts)

            idc = IDC.objects.filter(name=j_idc)
            if idc:
                j_idc = idc[0].id
            else:
                return httperror(request, '添加失败, 没有%s这个IDC' % j_idc)

            group_ids, dept_ids = [], []
            for group_name in j_group:
                group = BisGroup.objects.filter(name=group_name)
                if group:
                    group_id = group[0].id
                else:
                    return httperror(request, '添加失败, 没有%s这个主机组' % group_name)
                group_ids.append(group_id)

            for dept_name in j_dept:
                dept = DEPT.objects.filter(name=dept_name)
                if dept:
                    dept_id = dept[0].id
                else:
                    return httperror(request, '添加失败, 没有%s这个部门' % dept_name)
                dept_ids.append(dept_id)

            if is_group_admin(request) and not verify(request, asset_group=group_ids, edept=dept_ids):
                return httperror(request, '添加失败, 没有%s这个主机组' % group_name)

            if Asset.objects.filter(ip=str(j_ip)):
                return httperror(request, '添加失败, 改IP%s已存在' % j_ip)

            host_info = [j_ip, j_port, j_idc, j_type, group_ids, dept_ids, j_active, j_comment]
            db_host_insert(host_info)

        smg = u'批量添加添加成功'
        return my_render('jasset/host_add_multi.html', locals(), request)

    return my_render('jasset/host_add_multi.html', locals(), request)


@require_admin
def host_edit_batch(request):
    """ 批量修改主机 """
    if request.method == 'POST':
        len_table = request.POST.get('len_table')
        for i in range(int(len_table)):
            j_id = "editable[" + str(i) + "][j_id]"
            j_ip = "editable[" + str(i) + "][j_ip]"
            j_port = "editable[" + str(i) + "][j_port]"
            j_dept = "editable[" + str(i) + "][j_dept]"
            j_idc = "editable[" + str(i) + "][j_idc]"
            j_type = "editable[" + str(i) + "][j_type]"
            j_group = "editable[" + str(i) + "][j_group]"
            j_active = "editable[" + str(i) + "][j_active]"
            j_comment = "editable[" + str(i) + "][j_comment]"

            j_id = request.POST.get(j_id).strip()
            j_ip = request.POST.get(j_ip).strip()
            j_port = request.POST.get(j_port).strip()
            j_dept = request.POST.getlist(j_dept)
            j_idc = request.POST.get(j_idc).strip()
            j_type = request.POST.get(j_type).strip()
            j_group = request.POST.getlist(j_group)
            j_active = request.POST.get(j_active).strip()
            j_comment = request.POST.get(j_comment).strip()

            host_info = [j_id, j_ip, j_idc, j_port, j_type, j_group, j_dept, j_active, j_comment]
            batch_host_edit(host_info)

        return HttpResponseRedirect('/jasset/host_list/')


@require_login
def host_edit_common_batch(request):
    """ 普通用户批量修改主机别名 """
    u = get_session_user_info(request)[2]
    if request.method == 'POST':
        len_table = request.POST.get('len_table')
        for i in range(int(len_table)):
            j_id = "editable[" + str(i) + "][j_id]"
            j_alias = "editable[" + str(i) + "][j_alias]"
            j_id = request.POST.get(j_id, '').strip()
            j_alias = request.POST.get(j_alias, '').strip()
            a = Asset.objects.get(id=j_id)
            asset_alias = AssetAlias.objects.filter(user=u, host=a)
            if asset_alias:
                asset_alias = asset_alias[0]
                asset_alias.alias = j_alias
                asset_alias.save()
            else:
                AssetAlias.objects.create(user=u, host=a, alias=j_alias)
    return my_render('jasset/host_list_common.html')


@require_login
def host_list(request):
    """ 列出主机 """
    header_title, path1, path2 = u'查看主机', u'资产管理', u'查看主机'
    keyword = request.GET.get('keyword', '')
    dept_id = get_session_user_info(request)[3]
    dept = DEPT.objects.get(id=dept_id)
    did = request.GET.get('did', '')
    gid = request.GET.get('gid', '')
    sid = request.GET.get('sid', '')
    post_all = Asset.objects.all().order_by('ip')

    post_keyword_all = Asset.objects.filter(Q(ip__contains=keyword) |
                                            Q(idc__name__contains=keyword) |
                                            Q(bis_group__name__contains=keyword) |
                                            Q(comment__contains=keyword)).distinct().order_by('ip')
    if did:
        dept = DEPT.objects.get(id=did)
        posts = dept.asset_set.all()
        return my_render('jasset/host_list_nop.html', locals(), request)

    elif gid:
        posts = []
        user_group = UserGroup.objects.get(id=gid)
        perms = Perm.objects.filter(user_group=user_group)
        for perm in perms:
            for post in perm.asset_group.asset_set.all():
                posts.append(post)
        posts = list(set(posts))
        return my_render('jasset/host_list_nop.html', locals(), request)

    elif sid:
        posts = []
        user_group = UserGroup.objects.get(id=sid)
        perms = Perm.objects.filter(user_group=user_group)
        for perm in perms:
            for post in perm.asset_group.asset_set.all():
                posts.append(post)
        posts = list(set(posts))
        return my_render('jasset/host_list_nop.html', locals(), request)

    else:
        if is_super_user(request):
            if keyword:
                posts = post_keyword_all
            else:
                posts = post_all
            contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
            return my_render('jasset/host_list.html', locals(), request)

        elif is_group_admin(request):
            if keyword:
                posts = post_keyword_all.filter(dept=dept)
            else:
                posts = post_all.filter(dept=dept)

            contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
            return my_render('jasset/host_list.html', locals(), request)

        elif is_common_user(request):
            user_id, username = get_session_user_info(request)[0:2]
            posts = user_perm_asset_api(username)
            contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
            return my_render('jasset/host_list_common.html', locals(), request)


@require_admin
def host_del(request, offset):
    """ 删除主机 """
    if offset == 'multi':
        len_list = request.POST.get("len_list")
        for i in range(int(len_list)):
            key = "id_list[" + str(i) + "]"
            host_id = request.POST.get(key)
            db_host_delete(request, host_id)
    else:
        host_id = int(offset)
        db_host_delete(request, host_id)

    return HttpResponseRedirect('/jasset/host_list/')


@require_super_user
def host_edit(request):
    """ 修改主机 """
    header_title, path1, path2 = u'修改主机', u'资产管理', u'修改主机'
    actives = {1: u'激活', 0: u'禁用'}
    login_types = {'L': 'LDAP', 'M': 'MAP'}
    eidc = IDC.objects.all()
    egroup = BisGroup.objects.exclude(name='ALL')
    edept = DEPT.objects.all()
    host_id = request.GET.get('id', '')
    post = Asset.objects.filter(id=int(host_id))
    if post:
        post = post[0]
    else:
        return httperror(request, '没有此主机!')

    e_group = post.bis_group.all()
    e_dept = post.dept.all()

    if request.method == 'POST':
        j_ip = request.POST.get('j_ip', '')
        j_idc = request.POST.get('j_idc', '')
        j_port = request.POST.get('j_port', '')
        j_type = request.POST.get('j_type', '')
        j_dept = request.POST.getlist('j_dept', '')
        j_group = request.POST.getlist('j_group', '')
        j_active = request.POST.get('j_active', '')
        j_comment = request.POST.get('j_comment', '')

        host_info = [j_ip, j_port, j_idc, j_type, j_group, j_dept, j_active, j_comment, post]
        if j_type == 'M':
            j_user = request.POST.get('j_user')
            j_password = request.POST.get('j_password')
            db_host_update(host_info, j_user, j_password)
        else:
            db_host_update(host_info)

        smg = u'主机 %s 修改成功' % j_ip
        return HttpResponseRedirect('/jasset/host_detail/?id=%s' % host_id)

    return my_render('jasset/host_edit.html', locals(), request)


@require_admin
def host_edit_adm(request):
    """ 部门管理员修改主机 """
    header_title, path1, path2 = u'修改主机', u'资产管理', u'修改主机'
    actives = {1: u'激活', 0: u'禁用'}
    login_types = {'L': 'LDAP', 'M': 'MAP'}
    eidc = IDC.objects.all()
    dept = get_session_user_info(request)[5]
    egroup = BisGroup.objects.exclude(name='ALL').filter(dept=dept)
    host_id = request.GET.get('id', '')
    post = Asset.objects.filter(id=int(host_id))
    if post:
        post = post[0]
    else:
        return httperror(request, '没有此主机!')

    e_group = post.bis_group.all()

    if request.method == 'POST':
        j_ip = request.POST.get('j_ip')
        j_idc = request.POST.get('j_idc')
        j_port = request.POST.get('j_port')
        j_type = request.POST.get('j_type')
        j_dept = request.POST.getlist('j_dept')
        j_group = request.POST.getlist('j_group')
        j_active = request.POST.get('j_active')
        j_comment = request.POST.get('j_comment')

        host_info = [j_ip, j_port, j_idc, j_type, j_group, j_dept, j_active, j_comment]

        if not verify(request, asset_group=j_group, edept=j_dept):
            emg = u'修改失败,您无权操作!'
            return my_render('jasset/host_edit.html', locals(), request)

        if j_type == 'M':
            j_user = request.POST.get('j_user')
            j_password = request.POST.get('j_password')
            db_host_update(host_info, j_user, j_password, post)
        else:
            db_host_update(host_info, post)

        smg = u'主机 %s 修改成功' % j_ip
        return HttpResponseRedirect('/jasset/host_detail/?id=%s' % host_id)

    return my_render('jasset/host_edit.html', locals(), request)


@require_login
def host_detail(request):
    """ 主机详情 """
    header_title, path1, path2 = u'主机详细信息', u'资产管理', u'主机详情'
    host_id = request.GET.get('id', '')
    post = Asset.objects.filter(id=host_id)
    if not post:
        return httperror(request, '没有此主机!')
    post = post.first()

    if is_group_admin(request) and not verify(request, asset=[host_id]):
        return httperror(request, '您无权查看!')

    elif is_common_user(request):
        username = get_session_user_info(request)[1]
        user_permed_hosts = user_perm_asset_api(username)
        if post not in user_permed_hosts:
            return httperror(request, '您无权查看!')
    else:
        log_all = Log.objects.filter(host=post.ip)
        log, log_more = log_all[:10], log_all[10:]
        user_permed_list = asset_perm_api(post)

    return my_render('jasset/host_detail.html', locals(), request)


@require_super_user
def idc_add(request):
    """ 添加IDC """
    header_title, path1, path2 = u'添加IDC', u'资产管理', u'添加IDC'
    if request.method == 'POST':
        j_idc = request.POST.get('j_idc')
        j_comment = request.POST.get('j_comment')
        if IDC.objects.filter(name=j_idc):
            emg = u'该IDC已存在!'
            return my_render('jasset/idc_add.html', locals(), request)
        else:
            smg = u'IDC:%s添加成功' % j_idc
            IDC.objects.create(name=j_idc, comment=j_comment)

    return my_render('jasset/idc_add.html', locals(), request)


@require_admin
def idc_list(request):
    """ 列出IDC """
    header_title, path1, path2 = u'查看IDC', u'资产管理', u'查看IDC'
    dept_id = get_user_dept(request)
    dept = DEPT.objects.get(id=dept_id)
    keyword = request.GET.get('keyword', '')
    if keyword:
        posts = IDC.objects.filter(Q(name__contains=keyword) | Q(comment__contains=keyword))
    else:
        posts = IDC.objects.exclude(name='ALL').order_by('id')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
    return my_render('jasset/idc_list.html', locals(), request)


@require_super_user
def idc_edit(request):
    """ 修改IDC """
    header_title, path1, path2 = u'编辑IDC', u'资产管理', u'编辑IDC'
    idc_id = request.GET.get('id', '')
    idc = IDC.objects.filter(id=idc_id)
    if int(idc_id) == 1:
        return httperror(request, u'默认IDC不能编辑!')
    if idc:
        idc = idc[0]
        default = IDC.objects.get(id=1).asset_set.all()
        eposts = Asset.objects.filter(idc=idc).order_by('ip')
        posts = [g for g in default if g not in eposts]
    else:
        return httperror(request, u'此IDC不存在')

    if request.method == 'POST':
        idc_id = request.POST.get('id')
        j_idc = request.POST.get('j_idc')
        j_hosts = request.POST.getlist('j_hosts')
        j_comment = request.POST.get('j_comment')
        idc_default = request.POST.getlist('idc_default')

        idc = IDC.objects.filter(id=idc_id)
        if idc:
            idc.update(name=j_idc, comment=j_comment)
            for host_id in j_hosts:
                Asset.objects.filter(id=host_id).update(idc=idc[0])

            i = IDC.objects.get(id=1)
            for host in idc_default:
                g = Asset.objects.filter(id=host).update(idc=i)
        else:
            return httperror(request, u'此IDC不存在')

        return HttpResponseRedirect('/jasset/idc_list/?id=%s' % idc_id)

    return my_render('jasset/idc_edit.html', locals(), request)


@require_admin
def idc_detail(request):
    """ IDC详情 """
    header_title, path1, path2 = u'IDC详情', u'资产管理', u'IDC详情'
    login_types = {'L': 'LDAP', 'M': 'MAP'}
    idc_id = request.GET.get('id', '')
    idc_filter = IDC.objects.filter(id=idc_id)
    if idc_filter:
        idc = idc_filter[0]
    else:
        return httperror(request, '没有此IDC')
    dept = get_session_user_info(request)[5]
    if is_super_user(request):
        posts = Asset.objects.filter(idc=idc).order_by('ip')
    elif is_group_admin(request):
        posts = Asset.objects.filter(idc=idc, dept=dept).order_by('ip')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    return my_render('jasset/idc_detail.html', locals(), request)


@require_super_user
def idc_del(request):
    """ 删除IDC """
    offset = request.GET.get('id', '')
    if offset == 'multi':
        len_list = request.POST.get("len_list")
        for i in range(int(len_list)):
            key = "id_list[" + str(i) + "]"
            idc_id = request.POST.get(key)
            db_idc_delete(request, idc_id)
    else:
        db_idc_delete(request, int(offset))
    return HttpResponseRedirect('/jasset/idc_list/')


@require_admin
def group_add(request):
    """ 添加主机组 """
    header_title, path1, path2 = u'添加主机组', u'资产管理', u'添加主机组'
    if is_super_user(request):
        posts = Asset.objects.all()
        edept = DEPT.objects.all()
    elif is_group_admin(request):
        dept_id = get_user_dept(request)
        dept = DEPT.objects.get(id=dept_id)
        posts = Asset.objects.filter(dept=dept)
        edept = get_session_user_info(request)[5]

    if request.method == 'POST':
        j_group = request.POST.get('j_group', '')
        j_dept = request.POST.get('j_dept', '')
        j_hosts = request.POST.getlist('j_hosts', '')
        j_comment = request.POST.get('j_comment', '')

        try:
            if is_group_admin(request) and not verify(request, asset=j_hosts, edept=[j_dept]):
                emg = u'添加失败, 您无权操作!'
                raise RaiseError

            elif BisGroup.objects.filter(name=j_group):
                emg = u'添加失败, 该主机组已存在!'
                raise RaiseError

        except RaiseError:
            pass

        else:
            j_dept = DEPT.objects.filter(id=j_dept).first()
            group = BisGroup.objects.create(name=j_group, dept=j_dept, comment=j_comment)
            for host in j_hosts:
                g = Asset.objects.get(id=host)
                group.asset_set.add(g)
            smg = u'主机组 %s 添加成功' % j_group

    return my_render('jasset/group_add.html', locals(), request)


@require_admin
def group_list(request):
    """ 列出主机组 """
    header_title, path1, path2 = u'查看主机组', u'资产管理', u'查看主机组'
    dept_id = get_user_dept(request)
    dept = DEPT.objects.get(id=dept_id)
    keyword = request.GET.get('keyword', '')
    gid = request.GET.get('gid')
    sid = request.GET.get('sid')
    if gid:
        posts = []
        user_group = UserGroup.objects.get(id=gid)
        perms = Perm.objects.filter(user_group=user_group)
        for perm in perms:
            posts.append(perm.asset_group)

    elif sid:
        posts = []
        user_group = UserGroup.objects.get(id=sid)
        perms = Perm.objects.filter(user_group=user_group)
        for perm in perms:
            posts.append(perm.asset_group)

    else:
        if is_super_user(request):
            if keyword:
                posts = BisGroup.objects.exclude(name='ALL').filter(
                    Q(name__contains=keyword) | Q(comment__contains=keyword))
            else:
                posts = BisGroup.objects.exclude(name='ALL').order_by('id')
        elif is_group_admin(request):
            if keyword:
                posts = BisGroup.objects.filter(Q(name__contains=keyword) | Q(comment__contains=keyword)).filter(
                    dept=dept)
            else:
                posts = BisGroup.objects.filter(dept=dept).order_by('id')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
    return my_render('jasset/group_list.html', locals(), request)


@require_admin
def group_edit(request):
    """ 修改主机组 """
    header_title, path1, path2 = u'编辑主机组', u'资产管理', u'编辑主机组'
    group_id = request.GET.get('id', '')
    group = BisGroup.objects.get(id=group_id)
    host_all = Asset.objects.all()
    dept_id = get_user_dept(request)
    eposts = Asset.objects.filter(bis_group=group)

    if is_super_user(request):
        edept = DEPT.objects.all()
        posts = [g for g in host_all if g not in eposts]

    elif is_group_admin(request):
        if not verify(request, asset_group=[group_id]):
            return httperror(request, '编辑失败, 您无权操作!')
        dept = DEPT.objects.get(id=dept_id)
        all_dept = Asset.objects.filter(dept=dept)
        posts = [g for g in all_dept if g not in eposts]

    if request.method == 'POST':
        j_group = request.POST.get('j_group', '')
        j_hosts = request.POST.getlist('j_hosts', '')
        j_dept = request.POST.get('j_dept', '')
        j_comment = request.POST.get('j_comment', '')

        j_dept = DEPT.objects.filter(id=int(j_dept))
        j_dept = j_dept[0]

        group.asset_set.clear()
        for host in j_hosts:
            g = Asset.objects.get(id=host)
            group.asset_set.add(g)
        BisGroup.objects.filter(id=group_id).update(name=j_group, dept=j_dept, comment=j_comment)
        smg = u'主机组%s修改成功' % j_group
        return HttpResponseRedirect('/jasset/group_list')

    return my_render('jasset/group_edit.html', locals(), request)


@require_admin
def group_detail(request):
    """ 主机组详情 """
    header_title, path1, path2 = u'主机组详情', u'资产管理', u'主机组详情'
    login_types = {'L': 'LDAP', 'M': 'MAP'}
    dept = get_session_user_info(request)[5]
    group_id = request.GET.get('id', '')
    group = BisGroup.objects.get(id=group_id)
    if is_super_user(request):
        posts = Asset.objects.filter(bis_group=group).order_by('ip')

    elif is_group_admin(request):
        if not verify(request, asset_group=[group_id]):
            return httperror(request, u'您无权查看!')
        posts = Asset.objects.filter(bis_group=group).filter(dept=dept).order_by('ip')

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
    return my_render('jasset/group_detail.html', locals(), request)


@require_admin
def group_del_host(request):
    """ 主机组中剔除主机, 并不删除真实主机 """
    if request.method == 'POST':
        group_id = request.POST.get('group_id')
        offset = request.GET.get('id', '')
        group = BisGroup.objects.get(id=group_id)
        if offset == 'group':
            len_list = request.POST.get("len_list")
            for i in range(int(len_list)):
                key = "id_list[" + str(i) + "]"
                jid = request.POST.get(key)
                g = Asset.objects.get(id=jid)
                group.asset_set.remove(g)

    else:
        offset = request.GET.get('id', '')
        group_id = request.GET.get('gid', '')
        group = BisGroup.objects.get(id=group_id)
        g = Asset.objects.get(id=offset)
        group.asset_set.remove(g)

    return HttpResponseRedirect('/jasset/group_detail/?id=%s' % group.id)


@require_admin
def group_del(request):
    """ 删除主机组 """
    offset = request.GET.get('id', '')
    if offset == 'multi':
        len_list = request.POST.get("len_list")
        for i in range(int(len_list)):
            key = "id_list[" + str(i) + "]"
            gid = request.POST.get(key)
            if is_group_admin(request) and not verify(request, asset_group=[gid]):
                return httperror(request, '删除失败, 您无权删除!')
            BisGroup.objects.filter(id=gid).delete()
    else:
        gid = int(offset)
        if is_group_admin(request) and not verify(request, asset_group=[gid]):
            return httperror(request, '删除失败, 您无权删除!')
        BisGroup.objects.filter(id=gid).delete()
    return HttpResponseRedirect('/jasset/group_list/')


@require_admin
def dept_host_ajax(request):
    """ 添加主机组时, 部门联动主机异步 """
    dept_id = request.GET.get('id', '')
    if dept_id not in ['1', '2']:
        dept = DEPT.objects.filter(id=dept_id)
        if dept:
            dept = dept[0]
            hosts = dept.asset_set.all()
    else:
        hosts = Asset.objects.all()

    return my_render('jasset/dept_host_ajax.html', locals())


@require_login
def host_search(request):
    """ 搜索主机 """
    keyword = request.GET.get('keyword')
    login_types = {'L': 'LDAP', 'M': 'MAP'}
    dept = get_session_user_info(request)[5]
    post_all = Asset.objects.filter(Q(ip__contains=keyword) |
                                    Q(idc__name__contains=keyword) |
                                    Q(bis_group__name__contains=keyword) |
                                    Q(comment__contains=keyword)).distinct().order_by('ip')
    if is_super_user(request):
        posts = post_all

    elif is_group_admin(request):
        posts = post_all.filter(dept=dept)

    elif is_common_user(request):
        username = get_session_user_info(request)[2]
        post_perm = user_perm_asset_api(username)
        posts = list(set(post_all) & set(post_perm))

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    return my_render('jasset/host_search.html', locals(), request)