# -*- coding: utf-8 -*-


from django.db.models import Q
from jumpserver.api import *
from jperm.perm_api import *
from jperm.models import PermLog as Log
from jperm.models import SysUser
from juser.user_api import gen_ssh_key


from juser.models      import User, UserGroup
from jasset.models     import Asset, AssetGroup
from jperm.models      import PermRole, PermRule

from jperm.utils       import updates_dict, gen_keys, get_rand_pass
from jperm.ansible_api import Tasks
from jperm.perm_api    import get_role_info

from jumpserver.api    import my_render, get_object



@require_role('admin')
def perm_rule_list(request):
    """
    用户授权视图：
      该视图的模板包含2部分：
        1. block   部分：{% block content %}
             rander_content 为渲染数据
        2. include 部分：{% include 'nav_cat_bar.html' %}
             rander_nav 为渲染数据
    """
    data_nav = {"header_title": "授权规则", "path1": "规则管理", "path2": "查看规则"}

    # 获取所有规则
    rules_list = PermRule.objects.all()

    
    # TODO: 搜索和分页
    keyword = request.GET.get('search', '')
    if keyword:
        rules_list = rules_list.filter(Q(name=keyword))

    rules_list, p, rules, page_range, current_page, show_first, show_end = pages(rules_list, request)
    data_content = {"rules": rules_list}

    render_data = updates_dict(data_nav, data_content)
        
    return my_render('jperm/perm_rule_list.html', render_data, request)


@require_role('admin')
def perm_rule_detail(request):
    """
    用户详情视图：
      该视图的模板包含2部分：
        1. block   部分：{% block content %}
             rander_content 为渲染数据
        2. include 部分：{% include 'nav_cat_bar.html' %}
             rander_nav 为渲染数据
    """
    data_nav = {"header_title": "授权规则", "path1": "授权管理", "path2": "规则详情"}

    # 根据rule_id 取得rule对象
    rule_id = request.GET.get("id")
    rule_obj = PermRule.objects.get(id=rule_id)
    user_obj = rule_obj.user.all()
    asset_obj = rule_obj.asset.all()

    roles_name = [role.name for role in rule_obj.role.all()]
    data_content = {"roles_name": ','.join(roles_name), "rule": rule_obj, "users": user_obj, "assets": asset_obj}

    render_data = updates_dict(data_nav, data_content)

    return my_render('jperm/perm_rule_detail.html', render_data, request)
    

@require_role('admin')
def perm_rule_add(request):
    """

    :param request:
    :return:
    """
    data_nav = {"header_title": "授权规则", "path1": "授权管理", "path2": "添加规则"}

    if request.method == 'GET':
        # 获取所有 用户,用户组,资产,资产组,用户角色, 用于添加授权规则
        users = User.objects.all()
        user_groups = UserGroup.objects.all()
        assets = Asset.objects.all()
        asset_groups = AssetGroup.objects.all()
        roles = PermRole.objects.all()

        data_content = {"users": users, "user_groups": user_groups, 
                        "assets": assets, "asset_groups": asset_groups,
                        "roles": roles}
        render_data = updates_dict(data_nav, data_content)        
        return my_render('jperm/perm_rule_add.html', render_data, request)

    elif request.method == 'POST':
        # 获取用户选择的 用户,用户组,资产,资产组,用户角色
        users_select = request.POST.getlist('user', [])
        user_groups_select = request.POST.getlist('usergroup', [])
        assets_select = request.POST.getlist('asset', [])
        asset_groups_select = request.POST.getlist('assetgroup', [])
        roles_select = request.POST.getlist('role', [])
        rule_name = request.POST.get('rulename')
        rule_comment = request.POST.get('comment')

        # 获取需要授权的主机列表
        assets_obj = [Asset.objects.get(ip=asset) for asset in assets_select]
        asset_groups_obj = [AssetGroup.objects.get(name=group) for group in asset_groups_select]
        group_assets_obj = [asset for asset in [group.asset_set.all() for group in asset_groups_obj]]
        calc_assets = set(group_assets_obj) | set(assets_obj)

        # 获取需要授权的用户列表
        users_obj = [User.objects.get(name=user) for user in users_select]
        user_groups_obj = [UserGroup.objects.get(name=group) for group in user_groups_select]
        group_users_obj = [user for user in [group.user_set.all() for group in user_groups_obj]]
        calc_users = set(group_users_obj) | set(users_obj)

        # 获取授予的角色列表
        roles_obj = [PermRole.objects.get(name=role) for role in roles_select]

        # 调用Ansible API 执行授权 资源---Role---用户
        # 生成Inventory, 这里需要向CMDB 获取认证信息（1. password， 2, key）
        hosts = [{"hostname": asset.ip,
                  "port": asset.port,
                  "username": asset.username,
                  "password": asset.password} for asset in calc_assets]
        # 获取需要授权的角色名称
        roles = [role.name for role in roles_obj]
        # 调用Ansible API 执行 password方式的授权 TODO: Surport sudo
        tasks = Tasks(hosts)
        ret = tasks.add_multi_user(*roles)
        # TODO: 调用Ansible API 执行 key方式的授权

        # 计算授权成功和授权失败的主机 TODO: 记录成功和失败
        perm_sucess = {}
        perm_failed = {}
        for role, status in ret.get('action_info').iteritems():
            if status['status'] == 'failed':
                failed_ip = status['msg'].keys()
                perm_sucess[role] = [asset for asset in calc_assets if asset.ip not in failed_ip]
                perm_failed[role] = [asset for asset in calc_assets if asset.ip in failed_ip]

        if not perm_failed.values():
            # 仅授权成功的，写回数据库(授权规则,用户,用户组,资产,资产组,用户角色)
            rule = PermRule(name=rule_name, comment=rule_comment)
            rule.save()
            rule.user = users_obj
            rule.usergroup = user_groups_obj
            rule.asset = assets_obj
            rule.asset_group = asset_groups_obj
            rule.role = roles_obj
            rule.save()
            return HttpResponse(ret)
        else:
            return HttpResponse("add rule failed")


@require_role('admin')
def perm_rule_edit(request):
    """
    list rules
    :param request:
    :return:
    """

    data_nav = {"header_title": "授权规则", "path1": "授权管理", "path2": "编辑规则"}
    # 根据rule_id 取得rule对象
    rule_id = request.GET.get("id")
    rule_obj = PermRule.objects.get(id=rule_id)


    if request.method == 'GET' and rule_id:
        # 获取所有的rule对象
        users_obj = rule_obj.user.all()
        user_groups_obj = rule_obj.user_group.all()
        assets_obj = rule_obj.asset.all()
        asset_groups_obj = rule_obj.asset_group.all()
        roles_obj = rule_obj.role.all()

        data_content = {"users": users_obj, "user_groups": user_groups_obj,
                        "assets": assets_obj, "asset_groups": asset_groups_obj,
                        "roles": roles_obj, "rule": rule_obj}
        render_data = updates_dict(data_nav, data_content)
        return my_render('jperm/perm_rule_edit.html', render_data, request)

    elif request.method == 'POST' and rule_id:
        return HttpResponse("uncompleted")


@require_role('admin')
def perm_rule_delete(request):
    """
    use to delete rule
    :param request:
    :return:
    """
    if request.method == 'POST':
        # 根据rule_id 取得rule对象
        rule_id = request.POST.get("id")
        rule_obj = PermRule.objects.get(id=rule_id)
        print rule_id, rule_obj
        print rule_obj.name
        rule_obj.delete()
        return HttpResponse(u"删除授权规则：%s" % rule_obj.name)
    else:
        return HttpResponse(u"不支持该操作")


@require_role('admin')
def perm_role_list(request):
    """
    用户授权视图：
      该视图的模板包含2部分：
        1. block   部分：{% block content %}
             rander_content 为渲染数据
        2. include 部分：{% include 'nav_cat_bar.html' %}
             rander_nav 为渲染数据
    """
    data_nav = {"header_title": "系统角色", "path1": "角色管理", "path2": "查看角色"}

    # 获取所有系统角色
    roles_list = PermRole.objects.all()


    # TODO: 搜索和分页
    keyword = request.GET.get('search', '')
    if keyword:
        roles_list = roles_list.filter(Q(name=keyword))

    roles_list, p, roles, page_range, current_page, show_first, show_end = pages(roles_list, request)
    data_content = {"roles": roles_list}

    render_data = updates_dict(data_nav, data_content)

    return my_render('jperm/perm_role_list.html', render_data, request)


@require_role('admin')
def perm_role_add(request):
    """
    用户授权视图：
      该视图的模板包含2部分：
        1. block   部分：{% block content %}
             rander_content 为渲染数据
        2. include 部分：{% include 'nav_cat_bar.html' %}
             rander_nav 为渲染数据
    """
    data_nav = {"header_title": "系统角色", "path1": "角色管理", "path2": "添加角色"}

    if request.method == "GET":
        return my_render('jperm/perm_role_add.html', data_nav, request)

    elif request.method == "POST":
        # 获取参数： name, comment
        name = request.POST.get("role_name")
        comment = request.POST.get("role_comment")
        # 生成随机密码，生成秘钥对
        password = get_rand_pass()
        key_path = gen_keys()
        role = PermRole(name=name, comment=comment, password=password, key_path=key_path)
        role.save()
        return HttpResponse(u"添加角色: %s" % name)
    else:
        return HttpResponse(u"不支持该操作")

@require_role('admin')
def perm_role_delete(request):
    """
    用户授权视图：
      该视图的模板包含2部分：
        1. block   部分：{% block content %}
             rander_content 为渲染数据
        2. include 部分：{% include 'nav_cat_bar.html' %}
             rander_nav 为渲染数据
    """
    if request.method == "POST":
        # 获取参数删除的role对象
        role_id = request.POST.get("id")
        role = PermRole.objects.get(id=role_id)
        role_key = role.key_path
        # 删除存储的秘钥，以及目录
        key_files = os.listdir(role_key)
        for key_file in key_files:
            os.remove(os.path.join(role_key, key_file))
        os.rmdir(role_key)
        # 数据库里删除记录
        role.delete()
        return HttpResponse(u"删除角色: %s" % role.name)
    else:
        return HttpResponse(u"不支持该操作")


@require_role('admin')
def perm_role_detail(request):
    """
        the role_info data like:
            {'asset_groups': [],
            'assets': [<Asset: 192.168.10.148>],
            'rules': [<PermRule: PermRule object>],
            'user_groups': [],
            'users': [<User: user1>]}
    """
    data_nav = {"header_title": "系统角色", "path1": "角色管理", "path2": "角色详情"}

    if request.method == "GET":
        role_id = request.GET.get("id")
        role_info = get_role_info(role_id)
        render_data = updates_dict(data_nav, role_info)
        return my_render('jperm/perm_role_detail.html', render_data, request)


@require_role('admin')
def perm_role_edit(request):
    """

    :param request:
    :return:
    """
    data_nav = {"header_title": "系统角色", "path1": "角色管理", "path2": "角色编辑"}

    if request.method == "GET":
        role_id = request.GET.get("id")
        data_content = {"role": PermRole.objects.get(id=role_id)}
        render_data = updates_dict(data_nav, data_content)
        return my_render('jperm/perm_role_edit.html', render_data, request)

    if request.method == "POST":
        return HttpResponse(u"未实现")


@require_role('admin')
def perm_role_push(request):
    """

    :param request:
    :return:
    """
    data_nav = {"header_title": "系统角色", "path1": "角色管理", "path2": "角色推送"}

    if request.method == "GET":
        data_content = {"roles": PermRole.objects.all(),
                        "assets": Asset.objects.all(),
                        "asset_groups": AssetGroup.objects.all()}
        render_data = updates_dict(data_nav, data_content)
        return my_render('jperm/perm_role_push.html', render_data, request)

    if request.method == "POST":
        # 获取推荐角色的名称列表
        role_names = request.POST.getlist("roles")

        # 计算出需要推送的资产列表
        asset_ips = request.POST.getlist("assets")
        asset_group_names = request.POST.getlist("asset_groups")
        assets_obj = [Asset.objects.get(ip=asset_ip) for asset_ip in asset_ips]
        asset_groups_obj = [AssetGroup.objects.get(name=asset_group_name) for asset_group_name in asset_group_names]
        group_assets_obj = []
        for asset_group in asset_groups_obj:
            group_assets_obj.extend(asset_group.asset_set.all())
        calc_assets = set(assets_obj) | set(group_assets_obj)

        # 生成Inventory
        push_resource = [{"hostname": asset.ip,
                "port": asset.port,
                "username": asset.username,
                "password": asset.password} for asset in calc_assets]

        # 获取角色的推送方式,以及推送需要的信息
        roles_obj = [PermRole.objects.get(name=role_name) for role_name in role_names]
        role_pass = {}
        role_key = {}
        for role in roles_obj:
            role_pass[role.name] = role.password
            role_key[role.name] = os.path.join(role.key_path, 'id_rsa.pub')

        # 调用Ansible API 进行推送
        password_push = request.POST.get("use_password")
        key_push = request.POST.get("use_publicKey")
        task = Tasks(push_resource)
        ret = {}
        ret_failed = []
        if password_push:
            ret["password_push"] = task.add_multi_user(**role_pass)
            if ret["password_push"].get("status") != "success":
                ret_failed.append(1)
        if key_push:
            ret["key_push"] = task.push_multi_key(**role_key)
            if ret["key_push"].get("status") != "success":
                ret_failed.append(1)

        print ret
        if ret_failed:
            return HttpResponse(u"推送失败")
        else:
            return HttpResponse(u"推送系统角色： %s" % ','.join(role_names))









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

