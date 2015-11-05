# -*- coding: utf-8 -*-


from django.db.models import Q
from jumpserver.api import *
from jperm.perm_api import *
from jperm.models import PermLog as Log
from jperm.models import SysUser
from juser.user_api import gen_ssh_key


from juser.models     import User
from jasset.models    import Asset, AssetGroup

from jperm.utils      import updates_dict

from jumpserver.api   import my_render, get_object


@require_role('admin')
def perm_user_list(request):
    """
    用户授权视图：
      该视图的模板包含2部分：
        1. block   部分：{% block content %}
             rander_content 为渲染数据
        2. include 部分：{% include 'nav_cat_bar.html' %}
             rander_nav 为渲染数据
    """
    data_nav = {"header_title": "用户授权", "path1": "授权管理", "path2": "用户授权"}

    # 获取所有用户
    users_list = User.objects.all()
    
    # 搜索和分页
    keyword = request.GET.get('search', '')
    if keyword:
        users_list = users_list.filter(Q(name=keyword) | Q(username=keyword))
    users_list, p, users, page_range, current_page, show_first, show_end = pages(users_list, request)
    data_content = {"users": users}

    render_data = updates_dict(data_nav, data_content)
        
    return my_render('jperm/perm_user_list.html', render_data, request)


@require_role('admin')
def perm_user_detail(request):
    """
    用户详情视图：
      该视图的模板包含2部分：
        1. block   部分：{% block content %}
             rander_content 为渲染数据
        2. include 部分：{% include 'nav_cat_bar.html' %}
             rander_nav 为渲染数据
    """
    data_nav = {"header_title": "用户授权", "path1": "授权管理", "path2": "用户详情"}

    # 待实现
    render_data = updates_dict(data_nav)

    return my_render('jperm/perm_user_detail.html', render_data, request)
    

@require_role('admin')
def perm_user_edit(request):
    """
    TODO:
    """
    data_nav = {"header_title": "用户授权", "path1": "授权管理", "path2": "授权更改"}

    # 获取user对象
    user_id = request.GET.get('id', '')
    user = get_object(User, id=user_id)

    # 获取所有 资产 和 资产组
    asset_all = Asset.objects.all()
    asset_group_all = AssetGroup.objects.all()

    # 获取授权的 资产对象列表 和 资产组对象列表
    asset_permed = user.asset.all()
    asset_group_permed = user.asset_group.all()

    # 获取未授权的 资产对象列表 和 资产组对象列表
    if request.method == 'GET' and user:
        assets = [asset for asset in asset_all if asset not in asset_permed]
        asset_groups = [asset_group for asset_group in asset_group_all if asset_group not in asset_group_permed]
        data_content = {"assets": assets, "asset_groups": asset_groups, "user": user}

        render_data = updates_dict(data_nav, data_content)        
        return my_render('jperm/perm_user_edit.html', render_data, request)

    elif request.method == 'POST' and user:
        # 获取选择的资产列表 和 资产组列表
        asset_id_select = request.POST.getlist('asset_select', [])
        asset_group_id_select = request.POST.getlist('asset_groups_select', [])
        asset_select = get_object_list(Asset, asset_id_select)
        asset_group_select = get_object_list(AssetGroup, asset_group_id_select)

        # 新授权的资产对象列表, 回收权限的资产对象列表, 新授权的资产组对象列表, 回收的资产组对象列表
        asset_new = list(set(asset_select) - set(asset_permed))
        asset_del = list(set(asset_permed) - set(asset_select))
        asset_group_new = list(set(asset_group_select) - set(asset_group_permed))
        asset_group_del = list(set(asset_group_permed) - set(asset_group_select))

        for asset_group in asset_group_new:
            asset_new.extend(asset_group.asset_set.all())
        for asset_group in asset_group_del:
            asset_del.extend(asset_group.asset_set.all())
        perm_info = {
            'action': 'perm user edit: ' + user.name,
            'del': {'users': [user], 'assets': asset_del},
            'new': {'users': [user], 'assets': asset_new}
        }
        print perm_info
        try:
            results = perm_user_api(perm_info)  # 通过API授权或回收
        except ServerError, e:
            return HttpResponse(e)
        unreachable_asset = []
        failures_asset = []
        for ip in results.get('unreachable'):
            unreachable_asset.extend(filter(lambda x: x, Asset.objects.filter(ip=ip)))
        for ip in results.get('failures'):
            failures_asset.extend(filter(lambda x: x, Asset.objects.filter(ip=ip)))
        failures_asset.extend(unreachable_asset)  # 失败的授权要统计
        for asset in failures_asset:
            if asset in asset_select:
                asset_select.remove(asset)
            else:
                asset_select.append(asset)
        user.asset = asset_select
        user.asset_group = asset_group_select
        user.save()  # 保存到数据库
        return HttpResponse(json.dumps(results, sort_keys=True, indent=4), content_type="application/json")
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
    asset_permed = user_group.asset.all()  # 获取授权的资产对象列表
    asset_group_permed = user_group.asset_group.all()  # 获取授权的资产组对象列表
    if request.method == 'GET' and user_group:
        assets = [asset for asset in asset_all if asset not in asset_permed]
        asset_groups = [asset_group for asset_group in asset_group_all if asset_group not in asset_group_permed]
        return my_render('jperm/perm_group_edit.html', locals(), request)
    elif request.method == 'POST' and user_group:
        asset_id_select = request.POST.getlist('asset_select', [])
        asset_group_id_select = request.POST.getlist('asset_groups_select', [])
        asset_select = get_object_list(Asset, asset_id_select)
        asset_group_select = get_object_list(AssetGroup, asset_group_id_select)
        asset_new = list(set(asset_select) - set(asset_permed))  # 计算的得到新授权的资产对象列表
        asset_del = list(set(asset_permed) - set(asset_select))  # 计算得到回收权限的资产对象列表
        asset_group_new = list(set(asset_group_select) - set(asset_group_permed))  # 新授权的资产组对象列表
        asset_group_del = list(set(asset_group_permed) - set(asset_group_select))  # 回收的资产组对象列表
        users = user_group.user_set.all()
        perm_info = {
            'action': 'perm group edit: ' + user_group.name,
            'del': {'users': users, 'assets': asset_del},
            'new': {'users': users, 'assets': asset_new}
        }
        results = perm_user_api(perm_info)
        unreachable_asset = []
        failures_asset = []
        for ip in results.get('unreachable'):
            unreachable_asset.extend(filter(lambda x: x, Asset.objects.filter(ip=ip)))
        for ip in results.get('failures'):
            failures_asset.extend(filter(lambda x: x, Asset.objects.filter(ip=ip)))
        failures_asset.extend(unreachable_asset)  # 失败的授权要统计
        for asset in failures_asset:
            if asset in asset_select:
                asset_select.remove(asset)
            else:
                asset_select.append(asset)
        user_group.asset = asset_select
        user_group.asset_group = asset_group_select
        user_group.save()  # 保存到数据库
        return HttpResponse(json.dumps(results, sort_keys=True, indent=4), content_type="application/json")
    else:
        return HttpResponse('输入错误')


def log(request):
    header_title, path1, path2 = '授权记录', '授权管理', '授权记录'
    log_all = Log.objects.all().order_by('-datetime')
    log_all, p, logs, page_range, current_page, show_first, show_end = pages(log_all, request)
    return my_render('jperm/perm_log.html', locals(), request)


def sys_user_add(request):
    asset_group_all = AssetGroup.objects.all()
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        asset_groups_id = request.POST.getlist('asset_groups_select', [])
        comment = request.POST.get('comment')
        sys_user = SysUser(username=username, password=password, comment=comment)
        sys_user.save()
        gen_ssh_key(username, key_dir=os.path.join(SSH_KEY_DIR, 'sysuser'), authorized_keys=False)
        results = push_user(sys_user, asset_groups_id)
        return HttpResponse(json.dumps(results, sort_keys=True, indent=4), content_type="application/json")
    return my_render('jperm/sys_user_add.html', locals(), request)


def sys_user_list(request):
    users_list = SysUser.objects.all()
    users_list, p, users, page_range, current_page, show_first, show_end = pages(users_list, request)
    return my_render('jperm/sys_user_list.html', locals(), request)


def sys_user_edit(request):
    pass


def sys_user_del(request):
    pass

