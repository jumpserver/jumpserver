# coding:utf-8

import ast

from django.db.models import Q
from django.template import RequestContext
from django.shortcuts import get_object_or_404

from jasset.asset_api import *
from jumpserver.api import *
from jasset.forms import AssetForm
from jasset.models import Asset, IDC, AssetGroup, ASSET_TYPE, ASSET_STATUS


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
            smg = u"主机组 %s 添加成功" % name

    return my_render('jasset/group_add.html', locals(), request)


@require_role('admin')
def group_edit(request):
    """
    Edit asset group
    编辑资产组
    """
    header_title, path1, path2 = u'编辑主机组', u'资产管理', u'编辑主机组'
    group_id = request.GET.get('id', '')
    group = get_object(AssetGroup, id=group_id)

    asset_all = Asset.objects.all()
    asset_select = Asset.objects.filter(group=group)
    asset_no_select = [a for a in asset_all if a not in asset_select]

    if request.method == 'POST':
        name = request.POST.get('name', '')
        asset_select = request.POST.getlist('asset_select', [])
        comment = request.POST.get('comment', '')

        try:
            if not name:
                emg = u'组名不能为空'
                raise ServerError(emg)

            if group.name != name:
                asset_group_test = get_object(AssetGroup, name=name)
                if asset_group_test:
                    emg = u"该组名 %s 已存在" % name
                    raise ServerError(emg)

        except ServerError:
            pass

        else:
            group.asset_set.clear()
            db_update_group(id=group_id, name=name, comment=comment, asset_select=asset_select)
            smg = u"主机组 %s 添加成功" % name

        return HttpResponseRedirect('/jasset/group_list')

    return my_render('jasset/group_edit.html', locals(), request)


@require_role('admin')
def group_detail(request):
    """ 主机组详情 """
    header_title, path1, path2 = u'主机组详情', u'资产管理', u'主机组详情'
    group_id = request.GET.get('id', '')
    group = get_object(AssetGroup, id=group_id)
    asset_all = Asset.objects.filter(group=group).order_by('ip')

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(asset_all, request)
    return my_render('jasset/group_detail.html', locals(), request)


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
    af = AssetForm()
    if request.method == 'POST':
        af_post = AssetForm(request.POST)
        ip = request.POST.get('ip')

        try:
            if Asset.objects.filter(ip=str(ip)):
                error = u'该IP %s 已存在!' % ip
                raise ServerError(error)

        except ServerError:
            pass

        else:
            if af_post.is_valid():
                asset_save = af_post.save(commit=False)
                asset_save.save()
                af_post.save_m2m()
                msg = u'主机 %s 添加成功' % ip
            else:
                esg = u'主机 %s 添加失败' % ip

    return my_render('jasset/asset_add.html', locals(), request)


@require_role(role='user')
def asset_list(request):
    """
    list assets
    列出资产表
    """
    header_title, path1, path2 = u'查看主机', u'资产管理', u'查看主机'
    idc_all = IDC.objects.filter()
    asset_group_all = AssetGroup.objects.all()
    asset_type = ASSET_TYPE
    asset_status = ASSET_STATUS
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

    if request.method == 'POST':
        asset_batch = request.GET.get('arg', '')
        asset_id_all = str(request.POST.get('asset_id_all', ''))

        if asset_batch:
            for asset_id in asset_id_all.split(','):
                asset = get_object(Asset, id=asset_id)
                asset.delete()

    return HttpResponse(u'删除成功')


@require_role(role='super')
def asset_edit(request):
    """
    edit a asset
    修改主机
    """
    header_title, path1, path2 = u'修改资产', u'资产管理', u'修改资产'

    asset_id = request.GET.get('id', '')
    if not asset_id:
        return HttpResponse('没有该主机')
    asset = get_object(Asset, id=asset_id)
    af = AssetForm(instance=asset)
    if request.method == 'POST':
        af_post = AssetForm(request.POST, instance=asset)
        ip = request.POST.get('ip', '')

        # ip = request.POST.get('ip')
        # port = request.POST.get('port')
        # groups = request.POST.getlist('groups')
        # use_default_auth = True if request.POST.getlist('use_default_auth', []) else False
        # is_active = True if request.POST.get('is_active') else False
        # comment = request.POST.get('comment')

        # if not use_default_auth:
        #     username = request.POST.get('username')
        #     password = request.POST.get('password')
        #     if password == asset.password:
        #         password_encode = password
        #     else:
        #         password_encode = CRYPTOR.encrypt(password)
        # else:
        #     username = None
        #     password_encode = None

        try:
            asset_test = get_object(Asset, ip=ip)
            if asset_test and asset_id != str(asset_test.id):
                error = u'该IP %s 已存在!' % ip
                raise ServerError(error)
        except ServerError:
            pass
        else:
            if af_post.is_valid():
                af_save = af_post.save(commit=False)
                af_save.save()
                af_post.save_m2m()
                msg = u'主机 %s 修改成功' % ip
            else:
                emg = u'主机 %s 修改失败' % ip
            return HttpResponseRedirect('/jasset/asset_detail/?id=%s' % asset_id)

    return my_render('jasset/asset_edit.html', locals(), request)


@require_role('admin')
def asset_detail(request):
    """
    主机详情
    """
    header_title, path1, path2 = u'主机详细信息', u'资产管理', u'主机详情'
    asset_id = request.GET.get('id', '')
    asset = get_object(Asset, id=asset_id)

    return my_render('jasset/asset_detail.html', locals(), request)


@require_role('user')
def asset_search(request):
    """
    主机搜索
    """
    idc_all = IDC.objects.filter()
    asset_group_all = AssetGroup.objects.all()
    asset_type = ASSET_TYPE
    asset_status = ASSET_STATUS

    idc_name = request.GET.get('idc', '')
    group_name = request.GET.get('group', '')
    asset_type = request.GET.get('asset_type', '')
    status = request.GET.get('status', '')
    keyword = request.GET.get('keyword', '')

    if not idc_name and not asset_type and not status and group_name == 'all':
        select_number = 0
    else:
        select_number = 1

    if group_name == 'all':
        asset_find = Asset.objects.filter(
            idc__name__contains=idc_name,
            asset_type__contains=asset_type,
            status__contains=status
        )

    else:
        asset_find = Asset.objects.filter(
            idc__name__contains=idc_name,
            group__name__contains=group_name,
            asset_type__contains=asset_type,
            status__contains=status
        )
    if keyword and select_number == 1:
        asset_find = asset_find.filter(
            Q(hostname__contains=keyword) |
            Q(idc__name__contains=keyword) |
            Q(ip__contains=keyword) |
            Q(remote_ip__contains=keyword) |
            Q(comment__contains=keyword) |
            Q(group__name__contains=keyword) |
            Q(cpu__contains=keyword) |
            Q(memory__contains=keyword) |
            Q(disk__contains=keyword))

    elif keyword:
        asset_find = Asset.objects.filter(
            Q(hostname__contains=keyword) |
            Q(idc__name__contains=keyword) |
            Q(ip__contains=keyword) |
            Q(remote_ip__contains=keyword) |
            Q(comment__contains=keyword) |
            Q(group__name__contains=keyword) |
            Q(cpu__contains=keyword) |
            Q(memory__contains=keyword) |
            Q(disk__contains=keyword))

    # asset_find = list(set(asset_find))
    # asset_find_dic = {}
    # asset_find_lis = []
    # for server in asset_find:
    #     if server.ip:
    #         asset_find_dic[server.ip] = server
    #         asset_find_lis.append(server.ip)
    # sort_ip_list(asset_find_lis)
    # asset_find = []
    # for ip in asset_find_lis:
    #     asset_find.append(asset_find_dic[ip])
    # search_status = request.GET.get("_search", False)
    # if search_status:
    #     s = write_excel(asset_find)
    #     if s[0]:
    #         file_name = s[1]
    #         smg = 'excel文件已生成，请点击下载!'
    #         return my_render('cmdb/excel_download.html', locals(), request)
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(asset_find, request)
    return my_render('jasset/asset_list.html', locals(), request)