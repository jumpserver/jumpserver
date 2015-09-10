# coding:utf-8

import ast

from django.db.models import Q
from django.template import RequestContext
from django.shortcuts import get_object_or_404

from jperm.models import Perm
from jasset.asset_api import *
from jumpserver.api import *


@require_role('admin')
def group_add(request):
    """
    Add asset group
    添加资产组
    """
    header_title, path1, path2 = u'添加资产组', u'资产管理', u'添加资产组'
    asset_all = Asset.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '')
        asset_select = request.POST.getlist('asset_select', [])
        comment = request.POST.get('comment', '')

        try:
            if not name:
                error = u'组名不能为空'
                raise ServerError(error)

            asset_group_test = get_object(AssetGroup, name=name)
            if asset_group_test:
                error = u"该组名 %s 已存在" % name
                raise ServerError(error)

        except ServerError:
            pass
        else:
            db_add_group(name=name, comment=comment, asset_select=asset_select)
            msg = u"主机组 %s 添加成功" % name

    return my_render('jasset/group_add.html', locals(), request)


@require_role('admin')
def group_list(request):
    """
    list asset group
    列出资产组
    """
    header_title, path1, path2 = u'查看资产组', u'资产管理', u'查看资产组'
    keyword = request.GET.get('keyword', '')
    gid = request.GET.get('gid')
    sid = request.GET.get('sid')
    asset_group_list = AssetGroup.objects.all()

    if keyword:
        asset_group_list = asset_group_list.filter(Q(name__contains=keyword) | Q(comment__contains=keyword))

    asset_group_list, p, asset_groups, page_range, current_page, show_first, show_end = pages(asset_group_list, request)
    return my_render('jasset/group_list.html', locals(), request)


@require_role('admin')
def group_del(request):
    """
    del asset group
    删除主机组
    """
    group_ids = request.GET.get('id', '')
    group_id_list = group_ids.split(',')

    for group_id in group_id_list:
        AssetGroup.objects.filter(id=group_id).delete()

    return HttpResponse(u'删除成功')


@require_role('admin')
def asset_add(request):
    """
    Asset add view
    添加资产
    """
    header_title, path1, path2 = u'添加资产', u'资产管理', u'添加资产'
    asset_group_all = AssetGroup.objects.all()
    if request.method == 'POST':
        ip = request.POST.get('ip')
        port = request.POST.get('port')
        groups = request.POST.getlist('groups')
        use_default_auth = True if request.POST.getlist('use_default_auth', []) else False
        is_active = True if request.POST.get('is_active') else False
        comment = request.POST.get('comment')

        if not use_default_auth:
            username = request.POST.get('username')
            password = request.POST.get('password')
            password_encode = CRYPTOR.encrypt(password)
        else:
            username = None
            password_encode = None

        try:
            if Asset.objects.filter(ip=str(ip)):
                error = u'该IP %s 已存在!' % ip
                raise ServerError(error)

        except ServerError:
            pass
        else:
            db_asset_add(
                ip=ip, port=port, use_default_auth=use_default_auth, is_active=is_active, comment=comment,
                groups=groups, username=username, password=password_encode
            )

            msg = u'主机 %s 添加成功' % ip

    return my_render('jasset/asset_add.html', locals(), request)
#
#
# @require_admin
# def host_add_batch(request):
#     """ 批量添加主机 """
#     header_title, path1, path2 = u'批量添加主机', u'资产管理', u'批量添加主机'
#     login_types = {'LDAP': 'L', 'MAP': 'M'}
#     active_types = {'激活': 1, '禁用': 0}
#     dept_id = get_user_dept(request)
#     if request.method == 'POST':
#         multi_hosts = request.POST.get('j_multi').split('\n')
#         for host in multi_hosts:
#             if host == '':
#                 break
#             j_ip, j_port, j_type, j_idc, j_groups, j_depts, j_active, j_comment = host.split()
#             j_active = active_types[str(j_active)]
#             j_group = ast.literal_eval(j_groups)
#             j_dept = ast.literal_eval(j_depts)
#
#             if j_type not in ['LDAP', 'MAP']:
#                 return httperror(request, u'没有%s这种登录方式!' %j_type)
#
#             j_type = login_types[j_type]
#             idc = IDC.objects.filter(name=j_idc)
#             if idc:
#                 j_idc = idc[0].id
#             else:
#                 return httperror(request, '添加失败, 没有%s这个IDC' % j_idc)
#
#             group_ids, dept_ids = [], []
#             for group_name in j_group:
#                 group = BisGroup.objects.filter(name=group_name)
#                 if group:
#                     group_id = group[0].id
#                 else:
#                     return httperror(request, '添加失败, 没有%s这个主机组' % group_name)
#                 group_ids.append(group_id)
#
#             for dept_name in j_dept:
#                 dept = DEPT.objects.filter(name=dept_name)
#                 if dept:
#                     dept_id = dept[0].id
#                 else:
#                     return httperror(request, '添加失败, 没有%s这个部门' % dept_name)
#                 dept_ids.append(dept_id)
#
#             if is_group_admin(request) and not validate(request, asset_group=group_ids, edept=dept_ids):
#                 return httperror(request, '添加失败, 没有%s这个主机组' % group_name)
#
#             if Asset.objects.filter(ip=str(j_ip)):
#                 return httperror(request, '添加失败, 改IP%s已存在' % j_ip)
#
#             host_info = [j_ip, j_port, j_idc, j_type, group_ids, dept_ids, j_active, j_comment]
#             db_host_insert(host_info)
#
#         smg = u'批量添加添加成功'
#         return my_render('jasset/host_add_multi.html', locals(), request)
#
#     return my_render('jasset/host_add_multi.html', locals(), request)
#
#
# @require_admin
# def host_edit_batch(request):
#     """ 批量修改主机 """
#     if request.method == 'POST':
#         len_table = request.POST.get('len_table')
#         for i in range(int(len_table)):
#             j_id = "editable[" + str(i) + "][j_id]"
#             j_ip = "editable[" + str(i) + "][j_ip]"
#             j_port = "editable[" + str(i) + "][j_port]"
#             j_dept = "editable[" + str(i) + "][j_dept]"
#             j_idc = "editable[" + str(i) + "][j_idc]"
#             j_type = "editable[" + str(i) + "][j_type]"
#             j_group = "editable[" + str(i) + "][j_group]"
#             j_active = "editable[" + str(i) + "][j_active]"
#             j_comment = "editable[" + str(i) + "][j_comment]"
#
#             j_id = request.POST.get(j_id).strip()
#             j_ip = request.POST.get(j_ip).strip()
#             j_port = request.POST.get(j_port).strip()
#             j_dept = request.POST.getlist(j_dept)
#             j_idc = request.POST.get(j_idc).strip()
#             j_type = request.POST.get(j_type).strip()
#             j_group = request.POST.getlist(j_group)
#             j_active = request.POST.get(j_active).strip()
#             j_comment = request.POST.get(j_comment).strip()
#
#             host_info = [j_id, j_ip, j_idc, j_port, j_type, j_group, j_dept, j_active, j_comment]
#             batch_host_edit(host_info)
#
#         return HttpResponseRedirect('/jasset/host_list/')
#
#
# @require_role(role='user')
# def host_edit_common_batch(request):
#     """ 普通用户批量修改主机别名 """
#     u = get_session_user_info(request)[2]
#     if request.method == 'POST':
#         len_table = request.POST.get('len_table')
#         for i in range(int(len_table)):
#             j_id = "editable[" + str(i) + "][j_id]"
#             j_alias = "editable[" + str(i) + "][j_alias]"
#             j_id = request.POST.get(j_id, '').strip()
#             j_alias = request.POST.get(j_alias, '').strip()
#             a = Asset.objects.get(id=j_id)
#             asset_alias = AssetAlias.objects.filter(user=u, host=a)
#             if asset_alias:
#                 asset_alias = asset_alias[0]
#                 asset_alias.alias = j_alias
#                 asset_alias.save()
#             else:
#                 AssetAlias.objects.create(user=u, host=a, alias=j_alias)
#     return my_render('jasset/host_list_common.html', locals(), request)


@require_role(role='user')
def asset_list(request):
    """
    list assets
    列出资产表
    """
    header_title, path1, path2 = u'查看主机', u'资产管理', u'查看主机'
    keyword = request.GET.get('keyword', '')
    gid = request.GET.get('gid', '')  # asset group id
    sid = request.GET.get('sid', '')
    assets_list = Asset.objects.all().order_by('ip')

    if keyword:
        assets_list = assets_list.filter(Q(ip__contains=keyword) |
                                        Q(comment__contains=keyword)).distinct().order_by('ip')

    assets_list, p, assets, page_range, current_page, show_first, show_end = pages(assets_list, request)
    return my_render('jasset/asset_list.html', locals(), request)


@require_role('admin')
def asset_del(request):
    """
    del a asset
    删除主机
    """
    asset_id = request.GET.get('id', '')
    if asset_id:
        Asset.objects.filter(id=asset_id).delete()
        return HttpResponse(u'删除成功')
    return Http404


@require_role(role='super')
def asset_edit(request):
    """ 修改主机 """
    header_title, path1, path2 = u'修改资产', u'资产管理', u'修改资产'

    asset_id = request.GET.get('id', '')
    if not asset_id:
        return HttpResponse('没有该主机')
    asset = get_object(Asset, id=asset_id)

    if request.method == 'POST':
        ip = request.POST.get('ip')
        port = request.POST.get('port')
        groups = request.POST.getlist('groups')
        use_default_auth = True if request.POST.getlist('use_default_auth', []) else False
        is_active = True if request.POST.get('is_active') else False
        comment = request.POST.get('comment')

        if not use_default_auth:
            username = request.POST.get('username')
            password = request.POST.get('password')
            if password == asset.password:
                password_encode = password
            else:
                password_encode = CRYPTOR.encrypt(password)
        else:
            username = None
            password_encode = None

        try:
            asset_test = get_object(Asset, ip=ip)
            if asset_test and asset_id != str(asset_test.id):
                error = u'该IP %s 已存在!' % ip
                raise ServerError(error)
        except ServerError:
            pass
        else:
            db_asset_update(id=asset_id, ip=ip, port=port, use_default_auth=use_default_auth,
                            username=username, password=password_encode,
                            is_active=is_active, comment=comment)
            msg = u'主机 %s 修改成功' % ip
            return HttpResponseRedirect('/jasset/asset_detail/?id=%s' % asset_id)

    return my_render('jasset/asset_edit.html', locals(), request)


# @require_role(role='admin')
# def host_edit_adm(request):
#     """ 部门管理员修改主机 """
#     header_title, path1, path2 = u'修改主机', u'资产管理', u'修改主机'
#     actives = {1: u'激活', 0: u'禁用'}
#     login_types = {'L': 'LDAP', 'M': 'MAP'}
#     eidc = IDC.objects.all()
#     dept = get_session_user_info(request)[5]
#     egroup = BisGroup.objects.exclude(name='ALL').filter(dept=dept)
#     host_id = request.GET.get('id', '')
#     post = Asset.objects.filter(id=int(host_id))
#     if post:
#         post = post[0]
#     else:
#         return httperror(request, '没有此主机!')
#
#     e_group = post.bis_group.all()
#
#     if request.method == 'POST':
#         j_ip = request.POST.get('j_ip')
#         j_idc = request.POST.get('j_idc')
#         j_port = request.POST.get('j_port')
#         j_type = request.POST.get('j_type')
#         j_dept = request.POST.getlist('j_dept')
#         j_group = request.POST.getlist('j_group')
#         j_active = request.POST.get('j_active')
#         j_comment = request.POST.get('j_comment')
#
#         host_info = [j_ip, j_port, j_idc, j_type, j_group, j_dept, j_active, j_comment]
#
#         if not validate(request, asset_group=j_group, edept=j_dept):
#             emg = u'修改失败,您无权操作!'
#             return my_render('jasset/asset_edit.html', locals(), request)
#
#         if j_type == 'M':
#             j_user = request.POST.get('j_user')
#             j_password = request.POST.get('j_password')
#             db_host_update(host_info, j_user, j_password, post)
#         else:
#             db_host_update(host_info, post)
#
#         smg = u'主机 %s 修改成功' % j_ip
#         return HttpResponseRedirect('/jasset/host_detail/?id=%s' % host_id)
#
#     return my_render('jasset/asset_edit.html', locals(), request)


@require_role('admin')
def asset_detail(request):
    """ 主机详情 """
    header_title, path1, path2 = u'主机详细信息', u'资产管理', u'主机详情'
    asset_id = request.GET.get('id', '')
    asset = get_object(Asset, id=asset_id)

    return my_render('jasset/asset_detail.html', locals(), request)




#
#
# @require_admin
# def group_edit(request):
#     """ 修改主机组 """
#     header_title, path1, path2 = u'编辑主机组', u'资产管理', u'编辑主机组'
#     group_id = request.GET.get('id', '')
#     group = BisGroup.objects.filter(id=group_id)
#     if group:
#         group = group[0]
#     else:
#         httperror(request, u'没有这个主机组!')
#
#     host_all = Asset.objects.all()
#     dept_id = get_session_user_info(request)[3]
#     eposts = Asset.objects.filter(bis_group=group)
#
#     if is_group_admin(request) and not validate(request, asset_group=[group_id]):
#         return httperror(request, '编辑失败, 您无权操作!')
#     dept = DEPT.objects.filter(id=group.dept.id)
#     if dept:
#         dept = dept[0]
#     else:
#         return httperror(request, u'没有这个部门!')
#
#     all_dept = dept.asset_set.all()
#     posts = [g for g in all_dept if g not in eposts]
#
#     if request.method == 'POST':
#         j_group = request.POST.get('j_group', '')
#         j_hosts = request.POST.getlist('j_hosts', '')
#         j_dept = request.POST.get('j_dept', '')
#         j_comment = request.POST.get('j_comment', '')
#
#         j_dept = DEPT.objects.filter(id=int(j_dept))
#         j_dept = j_dept[0]
#
#         group.asset_set.clear()
#         for host in j_hosts:
#             g = Asset.objects.get(id=host)
#             group.asset_set.add(g)
#         BisGroup.objects.filter(id=group_id).update(name=j_group, dept=j_dept, comment=j_comment)
#         smg = u'主机组%s修改成功' % j_group
#         return HttpResponseRedirect('/jasset/group_list')
#
#     return my_render('jasset/group_edit.html', locals(), request)
#
#
# @require_admin
# def group_detail(request):
#     """ 主机组详情 """
#     header_title, path1, path2 = u'主机组详情', u'资产管理', u'主机组详情'
#     login_types = {'L': 'LDAP', 'M': 'MAP'}
#     dept = get_session_user_info(request)[5]
#     group_id = request.GET.get('id', '')
#     group = BisGroup.objects.get(id=group_id)
#     if is_super_user(request):
#         posts = Asset.objects.filter(bis_group=group).order_by('ip')
#
#     elif is_group_admin(request):
#         if not validate(request, asset_group=[group_id]):
#             return httperror(request, u'您无权查看!')
#         posts = Asset.objects.filter(bis_group=group).filter(dept=dept).order_by('ip')
#
#     contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
#     return my_render('jasset/group_detail.html', locals(), request)
#
#
# @require_admin
# def group_del_host(request):
#     """ 主机组中剔除主机, 并不删除真实主机 """
#     if request.method == 'POST':
#         group_id = request.POST.get('group_id')
#         offset = request.GET.get('id', '')
#         group = BisGroup.objects.get(id=group_id)
#         if offset == 'group':
#             len_list = request.POST.get("len_list")
#             for i in range(int(len_list)):
#                 key = "id_list[" + str(i) + "]"
#                 jid = request.POST.get(key)
#                 g = Asset.objects.get(id=jid)
#                 group.asset_set.remove(g)
#
#     else:
#         offset = request.GET.get('id', '')
#         group_id = request.GET.get('gid', '')
#         group = BisGroup.objects.get(id=group_id)
#         g = Asset.objects.get(id=offset)
#         group.asset_set.remove(g)
#
#     return HttpResponseRedirect('/jasset/group_detail/?id=%s' % group.id)
#

# @require_admin
# def dept_host_ajax(request):
#     """ 添加主机组时, 部门联动主机异步 """
#     dept_id = request.GET.get('id', '')
#     if dept_id not in ['1', '2']:
#         dept = DEPT.objects.filter(id=dept_id)
#         if dept:
#             dept = dept[0]
#             hosts = dept.asset_set.all()
#     else:
#         hosts = Asset.objects.all()
#
#     return my_render('jasset/dept_host_ajax.html', locals(), request)
#
#
# def show_all_ajax(request):
#     """ 批量修改主机时, 部门和组全部显示 """
#     env = request.GET.get('env', '')
#     get_id = request.GET.get('id', '')
#     host = Asset.objects.filter(id=get_id)
#     if host:
#         host = host[0]
#     return my_render('jasset/show_all_ajax.html', locals(), request)
#
#
# @require_login
# def host_search(request):
#     """ 搜索主机 """
#     keyword = request.GET.get('keyword')
#     login_types = {'L': 'LDAP', 'M': 'MAP'}
#     dept = get_session_user_info(request)[5]
#     post_all = Asset.objects.filter(Q(ip__contains=keyword) |
#                                     Q(idc__name__contains=keyword) |
#                                     Q(bis_group__name__contains=keyword) |
#                                     Q(comment__contains=keyword)).distinct().order_by('ip')
#     if is_super_user(request):
#         posts = post_all
#
#     elif is_group_admin(request):
#         posts = post_all.filter(dept=dept)
#
#     elif is_common_user(request):
#         user_id, username = get_session_user_info(request)[0:2]
#         post_perm = user_perm_asset_api(username)
#         posts = list(set(post_all) & set(post_perm))
#     contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
#
#     return my_render('jasset/host_search.html', locals(), request)