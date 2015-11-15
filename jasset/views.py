# coding:utf-8

import ast

from django.db.models import Q
from django.template import RequestContext
from django.shortcuts import get_object_or_404

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
        groups = request.POST.getlist('groups')
        use_default = True if request.POST.getlist('use_default', []) else False
        is_active = True if request.POST.get('is_active') else False
        comment = request.POST.get('comment')

        if not use_default:
            username = request.POST.get('username')
            password = request.POST.get('password')
            port = request.POST.get('port')
            password_encode = password
        else:
            username = None
            port = None
            password_encode = None

        try:
            if Asset.objects.filter(ip=str(ip)):
                error = u'该IP %s 已存在!' % ip
                raise ServerError(error)

        except ServerError:
            pass
        else:
            db_asset_add(
                ip=ip, port=port, use_default=use_default, is_active=is_active, comment=comment,
                groups=groups, username=username, password=password_encode
            )

            msg = u'主机 %s 添加成功' % ip

    return my_render('jasset/asset_add.html', locals(), request)


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
        groups = request.POST.getlist('groups')
        use_default = True if request.POST.getlist('use_default', []) else False
        is_active = True if request.POST.get('is_active') else False
        comment = request.POST.get('comment')

        if not use_default:
            username = request.POST.get('username')
            password = request.POST.get('password')
            port = request.POST.get('port')
            if password == asset.password:
                password_encode = password
            else:
                password_encode = CRYPTOR.encrypt(password)
        else:
            username = None
            password_encode = None
            port = 22

        try:
            asset_test = get_object(Asset, ip=ip)
            if asset_test and asset_id != str(asset_test.id):
                error = u'该IP %s 已存在!' % ip
                raise ServerError(error)
        except ServerError:
            pass
        else:
            db_asset_update(id=asset_id, ip=ip, port=port, use_default=use_default,
                            username=username, password=password_encode,
                            is_active=is_active, comment=comment)
            msg = u'主机 %s 修改成功' % ip
            return HttpResponseRedirect('/jasset/asset_detail/?id=%s' % asset_id)

    return my_render('jasset/asset_edit.html', locals(), request)


@require_role('admin')
def asset_detail(request):
    """ 主机详情 """
    header_title, path1, path2 = u'主机详细信息', u'资产管理', u'主机详情'
    asset_id = request.GET.get('id', '')
    asset = get_object(Asset, id=asset_id)

    return my_render('jasset/asset_detail.html', locals(), request)


