# # coding: utf-8
# import sys
#
# reload(sys)
# sys.setdefaultencoding('utf8')
#
# from django.shortcuts import render_to_response
# from django.template import RequestContext
# from jperm.models import Perm, SudoPerm, CmdGroup, Apply
from django.db.models import Q
from jperm.models import *
from jumpserver.api import *
from jperm.perm_api import *


@require_role('admin')
def perm_user_list(request):
    header_title, path1, path2 = '用户授权', '授权管理', '用户授权'
    keyword = request.GET.get('search', '')
    users_list = User.objects.all()  # 获取所有用户

    if keyword:
        users_list = users_list.filter(Q(name=keyword) | Q(username=keyword))  # 搜索
    users_list, p, users, page_range, current_page, show_first, show_end = pages(users_list, request)  # 分页

    return my_render('jperm/perm_user_list.html', locals(), request)


@require_role('admin')
def perm_user_edit(request):
    header_title, path1, path2 = '用户授权', '授权管理', '授权更改'
    user_id = request.GET.get('id', '')
    user = get_object(User, id=user_id)
    asset_all = Asset.objects.all()  # 获取所有资产
    asset_group_all = AssetGroup.objects.all()  # 获取所有资产组

    asset_id_list = user.assets.split(',')  # 获取授权的资产id列表
    asset_group_id_list = user.asset_groups.split(',')  # 获取授权的资产组id列表
    if request.method == 'GET' and user:
        asset_permed = get_object_list(Asset, asset_id_list)  # 获取授权的资产对象列表
        asset_group_permed = get_object_list(AssetGroup, asset_group_id_list)  # 获取授权的资产组对象列表
        assets = [asset for asset in asset_all if asset not in asset_permed]  # 获取没有授权的资产对象列表
        asset_groups = [asset_group for asset_group in asset_group_all if asset_group not in asset_group_permed] # 同理
        return my_render('jperm/perm_user_edit.html', locals(), request)

    elif request.method == 'POST' and user:
        asset_select = request.POST.getlist('asset_select', [])  # 获取选择的资产id列表
        asset_group_select = request.POST.getlist('asset_groups_select', [])  # 获取选择的资产组id列表
        asset_new = list(set(asset_select) - set(asset_id_list))  # 计算的得到新授权的资产对象列表
        asset_del = list(set(asset_id_list) - set(asset_select))  # 计算得到回收权限的资产对象列表
        asset_group_new = list(set(asset_group_select) - set(asset_group_id_list))  # 新授权的资产组对象列表
        asset_group_del = list(set(asset_group_id_list) - set(asset_group_select))  # 回收的资产组对象列表
        user.assets = ','.join(asset_select)  # 获取选择的资产id字符串 '1, 2 ,3'
        user.asset_groups = ','.join(asset_group_select)  # 获取选择的资产组id字符串 '2, 3'
        user.save()  # 保存到数据库

        perm_user_api(asset_new, asset_del, asset_group_new, asset_group_del, user=user)  # 通过API授权或回收

        return HttpResponseRedirect('/jperm/user/')

    else:
        return HttpResponse('输入错误')


@require_role('admin')
def perm_group_list(request):
    header_title, path1, path2 = '用户组授权', '授权管理', '用户组授权'
    keyword = request.GET.get('search', '')
    user_groups_list = UserGroup.objects.all()

    if keyword:
        request = user_groups_list.filter(Q(name=keyword) | Q(comment=keyword))
    user_groups_list, p, user_groups, page_range, current_page, show_first, show_end = pages(user_groups_list, request)

    return my_render('jperm/perm_group_list.html', locals(), request)


@require_role('admin')
def perm_group_edit(request):
    header_title, path1, path2 = '用户组授权', '授权管理', '授权更改'
    user_group_id = request.GET.get('id', '')
    user_group = get_object(UserGroup, id=user_group_id)
    asset_all = Asset.objects.all()
    asset_group_all = AssetGroup.objects.all()

    asset_id_list = user_group.assets.split(',')
    asset_group_id_list = user_group.asset_groups.split(',')
    print asset_id_list, asset_group_id_list
    if request.method == 'GET' and user_group:
        asset_permed = get_object_list(Asset, asset_id_list)
        asset_group_permed = get_object_list(AssetGroup, asset_group_id_list)
        assets = [asset for asset in asset_all if asset not in asset_permed]
        asset_groups = [asset_group for asset_group in asset_group_all if asset_group not in asset_group_permed]
        return my_render('jperm/perm_group_edit.html', locals(), request)

    elif request.method == 'POST' and user_group:
        asset_select = request.POST.getlist('asset_select', [])
        asset_group_select = request.POST.getlist('asset_groups_select', [])
        asset_new = list(set(asset_select) - set(asset_id_list))
        asset_del = list(set(asset_id_list) - set(asset_select))
        asset_group_new = list(set(asset_group_select) - set(asset_group_id_list))
        asset_group_del = list(set(asset_group_id_list) - set(asset_group_select))
        user_group.assets = ','.join(asset_select)
        user_group.asset_groups = ','.join(asset_group_select)
        user_group.save()

        perm_user_api(asset_new, asset_del, asset_group_new, asset_group_del, user_group=user_group)

        return HttpResponseRedirect('/jperm/group/')

    else:
        return HttpResponse('输入错误')



