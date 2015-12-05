# -*- coding: utf-8 -*-

from django.db.models import Q
from paramiko import SSHException
from jperm.perm_api import *
from juser.user_api import gen_ssh_key

from juser.models      import User, UserGroup
from jasset.models     import Asset, AssetGroup
from jperm.models      import PermRole, PermRule, PermSudo, PermPush
from jumpserver.models import Setting

from jperm.utils       import updates_dict, gen_keys, get_rand_pass, get_add_sudo_script
from jperm.ansible_api import MyTask
from jperm.perm_api    import get_role_info, get_role_push_host
from jumpserver.api    import my_render, get_object, CRYPTOR


@require_role('admin')
def perm_rule_list(request):
    """
    list rule page
    """
    # 渲染数据
    header_title, path1, path2 = "授权规则", "规则管理", "查看规则"
    # 获取所有规则
    rules_list = PermRule.objects.all()
    rule_id = request.GET.get('id')
    # TODO: 搜索和分页
    keyword = request.GET.get('search', '')
    if rule_id:
        rules_list = rules_list.filter(id=rule_id)

    if keyword:
        rules_list = rules_list.filter(Q(name=keyword))

    rules_list, p, rules, page_range, current_page, show_first, show_end = pages(rules_list, request)
        
    return my_render('jperm/perm_rule_list.html', locals(), request)


@require_role('admin')
def perm_rule_detail(request):
    """
    rule detail page
    """
    # 渲染数据
    header_title, path1, path2 = "授权规则", "规则管理", "规则详情"

    # 根据rule_id 取得rule对象
    rule_id = request.GET.get("id")
    rule_obj = PermRule.objects.get(id=rule_id)
    user_obj = rule_obj.user.all()
    asset_obj = rule_obj.asset.all()
    roles_name = [role.name for role in rule_obj.role.all()]

    # 渲染数据
    roles_name = ','.join(roles_name)
    rule = rule_obj
    users = user_obj
    assets = asset_obj

    return my_render('jperm/perm_rule_detail.html', locals(), request)


def perm_rule_add(request):
    """
    add rule page
    """
    # 渲染数据
    header_title, path1, path2 = "授权规则", "规则管理", "添加规则"

    # 渲染数据, 获取所有 用户,用户组,资产,资产组,用户角色, 用于添加授权规则
    users = User.objects.all()
    user_groups = UserGroup.objects.all()
    assets = Asset.objects.all()
    asset_groups = AssetGroup.objects.all()
    roles = PermRole.objects.all()

    if request.method == 'POST':
        # 获取用户选择的 用户,用户组,资产,资产组,用户角色
        users_select = request.POST.getlist('user', [])  # 需要授权用户
        user_groups_select = request.POST.getlist('usergroup', [])  # 需要授权用户组
        assets_select = request.POST.getlist('asset', [])  # 需要授权资产
        asset_groups_select = request.POST.getlist('assetgroup', [])  # 需要授权资产组
        roles_select = request.POST.getlist('role', [])  # 需要授权角色
        rule_name = request.POST.get('rulename')
        rule_comment = request.POST.get('rule_comment')

        try:
            rule = get_object(PermRule, name=rule_name)
            if rule:
                raise ServerError(u'授权规则 %s 已存在' % rule_name)

            # 获取需要授权的主机列表
            assets_obj = [Asset.objects.get(id=asset_id) for asset_id in assets_select]
            asset_groups_obj = [AssetGroup.objects.get(id=group_id) for group_id in asset_groups_select]
            group_assets_obj = []
            for asset_group in asset_groups_obj:
                group_assets_obj.extend(list(asset_group.asset_set.all()))
            calc_assets = set(group_assets_obj) | set(assets_obj)  # 授权资产和资产组包含的资产

            # 获取需要授权的用户列表
            users_obj = [User.objects.get(id=user_id) for user_id in users_select]
            user_groups_obj = [UserGroup.objects.get(id=group_id) for group_id in user_groups_select]
            # group_users_obj = [user for user in [group.user_set.all() for group in user_groups_obj]]
            # calc_users = set(group_users_obj) | set(users_obj)

            # 获取授予的角色列表
            roles_obj = [PermRole.objects.get(id=role_id) for role_id in roles_select]
            need_push_asset = set()

            for role in roles_obj:
                asset_no_push = get_role_push_host(role=role)[0]  # 获取某角色已经推送的资产
                need_push_asset.update(set(calc_assets) - set(asset_no_push))
                if need_push_asset:
                    raise ServerError(u'没有推送角色 %s 的主机 %s'
                                      % (role.name, ','.join([asset.hostname for asset in need_push_asset])))

            # 仅授权成功的，写回数据库(授权规则,用户,用户组,资产,资产组,用户角色)
            rule = PermRule(name=rule_name, comment=rule_comment)
            rule.save()
            rule.user = users_obj
            rule.user_group = user_groups_obj
            rule.asset = assets_obj
            rule.asset_group = asset_groups_obj
            rule.role = roles_obj
            rule.save()

            msg = u"添加授权规则：%s" % rule.name
            return HttpResponseRedirect('/jperm/rule/')
        except ServerError, e:
            error = e
    return my_render('jperm/perm_rule_add.html', locals(), request)


@require_role('admin')
def perm_rule_edit(request):
    """
    edit rule page
    """
    # 渲染数据
    header_title, path1, path2 = "授权规则", "规则管理", "添加规则"

    # 根据rule_id 取得rule对象
    rule_id = request.GET.get("id")
    rule = PermRule.objects.get(id=rule_id)

    if request.method == 'GET' and rule_id:
        # 渲染数据, 获取所选的rule对象
        rule_comment = rule.comment
        users_select = rule.user.all()
        user_groups_select = rule.user_group.all()
        assets_select = rule.asset.all()
        asset_groups_select = rule.asset_group.all()
        roles_select = rule.role.all()

        users = User.objects.all()
        user_groups = UserGroup.objects.all()
        assets = Asset.objects.all()
        asset_groups = AssetGroup.objects.all()
        roles = PermRole.objects.all()
        return my_render('jperm/perm_rule_edit.html', locals(), request)

    elif request.method == 'POST' and rule_id:
        # 获取用户选择的 用户,用户组,资产,资产组,用户角色
        rule_name = request.POST.get('rule_name')
        rule_comment = request.POST.get("rule_comment")
        users_select = request.POST.getlist('user', [])
        user_groups_select = request.POST.getlist('usergroup', [])
        assets_select = request.POST.getlist('asset', [])
        asset_groups_select = request.POST.getlist('assetgroup', [])
        roles_select = request.POST.getlist('role', [])

        assets_obj = [Asset.objects.get(id=asset_id) for asset_id in assets_select]
        asset_groups_obj = [AssetGroup.objects.get(id=group_id) for group_id in asset_groups_select]
        # group_assets_obj = [asset for asset in [group.asset_set.all() for group in asset_groups_obj]]
        # calc_assets = set(group_assets_obj) | set(assets_obj)

        # 获取需要授权的用户列表
        users_obj = [User.objects.get(id=user_id) for user_id in users_select]
        user_groups_obj = [UserGroup.objects.get(id=group_id) for group_id in user_groups_select]
        # group_users_obj = [user for user in [group.user_set.all() for group in user_groups_obj]]
        # calc_users = set(group_users_obj) | set(users_obj)

        # 获取授予的角色列表
        roles_obj = [PermRole.objects.get(id=role_id) for role_id in roles_select]

        # 仅授权成功的，写回数据库(授权规则,用户,用户组,资产,资产组,用户角色)
        rule.user = users_obj
        rule.user_group = user_groups_obj
        rule.asset = assets_obj
        rule.asset_group = asset_groups_obj
        rule.role = roles_obj
        rule.name = rule_name
        rule.comment = rule.comment
        rule.save()

        msg = u"更新授权规则：%s" % rule.name

    return HttpResponseRedirect('/jperm/rule/')


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
        rule_obj.delete()
        return HttpResponse(u"删除授权规则：%s" % rule_obj.name)
    else:
        return HttpResponse(u"不支持该操作")


@require_role('admin')
def perm_role_list(request):
    """
    list role page
    """
    # 渲染数据
    header_title, path1, path2 = "系统角色", "角色管理", "查看角色"

    # 获取所有系统角色
    roles_list = PermRole.objects.all()
    role_id = request.GET.get('id')
    # TODO: 搜索和分页
    keyword = request.GET.get('search', '')
    if keyword:
        roles_list = roles_list.filter(Q(name=keyword))

    if role_id:
        roles_list = roles_list.filter(id=role_id)

    roles_list, p, roles, page_range, current_page, show_first, show_end = pages(roles_list, request)

    return my_render('jperm/perm_role_list.html', locals(), request)


@require_role('admin')
def perm_role_add(request):
    """
    add role page
    """
    # 渲染数据
    header_title, path1, path2 = "系统角色", "角色管理", "添加角色"
    sudos = PermSudo.objects.all()

    if request.method == "POST":
        # 获取参数： name, comment
        name = request.POST.get("role_name", "")
        comment = request.POST.get("role_comment", "")
        password = request.POST.get("role_password", "")
        key_content = request.POST.get("role_key", "")
        sudo_ids = request.POST.getlist('sudo_name')

        try:
            if get_object(PermRole, name=name):
                raise ServerError('已经存在该用户 %s' % name)
            default = get_object(Setting, name='default')

            if password:
                encrypt_pass = CRYPTOR.encrypt(password)
            else:
                encrypt_pass = CRYPTOR.encrypt(CRYPTOR.gen_rand_pass(20))
            # 生成随机密码，生成秘钥对
            sudos_obj = [get_object(PermSudo, id=sudo_id) for sudo_id in sudo_ids]
            if key_content:
                key_path = gen_keys(key=key_content)
            else:
                key_path = gen_keys()
            logger.debug('generate role key: %s' % key_path)
            role = PermRole(name=name, comment=comment, password=encrypt_pass, key_path=key_path)
            role.save()
            role.sudo = sudos_obj
            msg = u"添加角色: %s" % name
            return HttpResponseRedirect('/jperm/role/')
        except ServerError, e:
            error = e

    return my_render('jperm/perm_role_add.html', locals(), request)


@require_role('admin')
def perm_role_delete(request):
    """
    delete role page
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
    the role detail page
        the role_info data like:
            {'asset_groups': [],
            'assets': [<Asset: 192.168.10.148>],
            'rules': [<PermRule: PermRule object>],
            '': [],
            '': [<User: user1>]}
    """
    # 渲染数据
    header_title, path1, path2 = "系统角色", "角色管理", "角色详情"

    if request.method == "GET":
        role_id = request.GET.get("id")
        role = get_object(PermRole, id=role_id)
        role_info = get_role_info(role_id)

        # 渲染数据
        rules = role_info.get("rules")
        assets = role_info.get("assets")
        asset_groups = role_info.get("asset_groups")
        users = role_info.get("users")
        user_groups = role_info.get("user_groups")
        pushed_asset, need_push_asset = get_role_push_host(get_object(PermRole, id=role_id))

        return my_render('jperm/perm_role_detail.html', locals(), request)


@require_role('admin')
def perm_role_edit(request):
    """
    edit role page
    """
    # 渲染数据
    header_title, path1, path2 = "系统角色", "角色管理", "角色编辑"

    # 渲染数据
    role_id = request.GET.get("id")
    role = PermRole.objects.get(id=role_id)
    role_pass = CRYPTOR.decrypt(role.password)
    sudo_all = PermSudo.objects.all()
    role_sudos = role.sudo.all()
    sudo_all = PermSudo.objects.all()
    if request.method == "GET":
        return my_render('jperm/perm_role_edit.html', locals(), request)

    if request.method == "POST":
        # 获取 POST 数据
        role_name = request.POST.get("role_name")
        role_password = request.POST.get("role_password")
        role_comment = request.POST.get("role_comment")
        role_sudo_names = request.POST.getlist("sudo_name")
        role_sudos = [PermSudo.objects.get(id=sudo_id) for sudo_id in role_sudo_names]
        key_content = request.POST.get("role_key", "")

        try:
            if not role:
                raise ServerError('角色用户不能存在')

            if role_password:
                encrypt_pass = CRYPTOR.encrypt(role_password)
                role.password = encrypt_pass
            # 生成随机密码，生成秘钥对
            if key_content:
                try:
                    key_path = gen_keys(key=key_content, key_path_dir=role.key_path)
                except SSHException:
                    raise ServerError('输入的密钥不合法')
                logger.debug('Recreate role key: %s' % role.key_path)
            # 写入数据库
            role.name = role_name
            role.comment = role_comment
            role.sudo = role_sudos

            role.save()
            msg = u"更新系统角色： %s" % role.name
            return HttpResponseRedirect('/jperm/role/')
        except ServerError, e:
            error = e

    return my_render('jperm/perm_role_edit.html', locals(), request)


@require_role('admin')
def perm_role_push(request):
    """
    the role push page
    """
    # 渲染数据
    header_title, path1, path2 = "系统角色", "角色管理", "角色推送"
    role_id = request.GET.get('id')
    asset_ids = request.GET.get('asset_id')
    role = get_object(PermRole, id=role_id)
    assets = Asset.objects.all()
    asset_groups = AssetGroup.objects.all()
    if asset_ids:
        need_push_asset = [get_object(Asset, id=asset_id) for asset_id in asset_ids.split(',')]

    if request.method == "POST":
        # 获取推荐角色的名称列表
        # 计算出需要推送的资产列表
        asset_ids = request.POST.getlist("assets")
        asset_group_ids = request.POST.getlist("asset_groups")
        assets_obj = [Asset.objects.get(id=asset_id) for asset_id in asset_ids]
        asset_groups_obj = [AssetGroup.objects.get(id=asset_group_id) for asset_group_id in asset_group_ids]
        group_assets_obj = []
        for asset_group in asset_groups_obj:
            group_assets_obj.extend(asset_group.asset_set.all())
        calc_assets = list(set(assets_obj) | set(group_assets_obj))
        push_resource = gen_resource(calc_assets)
        logger.debug('Push role res: %s' % push_resource)

        # 调用Ansible API 进行推送
        password_push = True if request.POST.get("use_password") else False
        key_push = True if request.POST.get("use_publicKey") else False
        task = MyTask(push_resource)
        ret = {}

        # 因为要先建立用户，所以password 是必选项，而push key是在 password也完成的情况下的 可选项
        # 1. 以秘钥 方式推送角色
        if key_push:
            ret["pass_push"] = task.add_user(role.name, CRYPTOR.decrypt(role.password))
            ret["key_push"] = task.push_key(role.name, os.path.join(role.key_path, 'id_rsa.pub'))

        # 2. 推送账号密码
        elif password_push:
            ret["pass_push"] = task.add_user(role.name, CRYPTOR.decrypt(role.password))

        # 3. 推送sudo配置文件
        if password_push or key_push:
            role_chosen_aliase = {}  # {'dev': 'NETWORKING, SHUTDOWN'}
            sudo_alias = set([sudo for sudo in role.sudo.all()])  # set(sudo1, sudo2, sudo3)
            if sudo_alias:
                role_chosen_aliase[role.name] = ','.join(sudo.name for sudo in sudo_alias if sudo.name)
                add_sudo_script = get_add_sudo_script(role_chosen_aliase, sudo_alias)
                ret['sudo'] = task.push_sudo_file(add_sudo_script)
                os.remove(add_sudo_script)

        logger.debug('推送role结果: %s' % ret)
        success_asset = {}
        failed_asset = {}
        logger.debug(ret)
        for push_type, result in ret.items():
            if result.get('failed'):
                for hostname, info in result.get('failed').items():
                    if hostname in failed_asset.keys():
                        if info in failed_asset.get(hostname):
                            failed_asset[hostname] += info
                    else:
                        failed_asset[hostname] = info

        for push_type, result in ret.items():
            if result.get('ok'):
                for hostname, info in result.get('ok').items():
                    if hostname in failed_asset.keys():
                        continue
                    elif hostname in success_asset.keys():
                        if str(info) in success_asset.get(hostname, ''):
                            success_asset[hostname] += str(info)
                    else:
                        success_asset[hostname] = str(info)

        # 推送成功 回写push表
        for asset in calc_assets:
            push_check = PermPush.objects.filter(role=role, asset=asset)
            if push_check:
                func = push_check.update
            else:
                def func(**kwargs):
                    PermPush(**kwargs).save()

            if failed_asset.get(asset.hostname):
                func(is_password=password_push, is_public_key=key_push, role=role, asset=asset, success=False,
                     result=failed_asset.get(asset.hostname))
            else:
                func(is_password=password_push, is_public_key=key_push, role=role, asset=asset, success=True)

        if not failed_asset:
            msg = u'角色 %s 推送成功[ %s ]' % (role.name, ','.join(success_asset.keys()))
        else:
            error = u'角色 %s 推送失败 [ %s ], 推送成功 [ %s ]' % (role.name,
                                                                ','.join(failed_asset.keys()),
                                                                ','.join(success_asset.keys()))
    return my_render('jperm/perm_role_push.html', locals(), request)


@require_role('admin')
def perm_sudo_list(request):
    """
    list sudo commands alias
    :param request:
    :return:
    """
    # 渲染数据
    header_title, path1, path2 = "Sudo命令", "别名管理", "查看别名"

    # 获取所有sudo 命令别名
    sudos_list = PermSudo.objects.all()

    # TODO: 搜索和分页
    keyword = request.GET.get('search', '')
    if keyword:
        sudos_list = sudos_list.filter(Q(name=keyword))

    sudos_list, p, sudos, page_range, current_page, show_first, show_end = pages(sudos_list, request)

    return my_render('jperm/perm_sudo_list.html', locals(), request)


@require_role('admin')
def perm_sudo_add(request):
    """
    list sudo commands alias
    :param request:
    :return:
    """
    # 渲染数据
    header_title, path1, path2 = "Sudo命令", "别名管理", "添加别名"

    if request.method == "POST":
        # 获取参数： name, comment
        name = request.POST.get("sudo_name").strip()
        comment = request.POST.get("sudo_comment").strip()
        commands = request.POST.get("sudo_commands").strip()

        if get_object(PermSudo, name=name):
            error = 'Sudo别名 %s已经存在' % name
        else:
            sudo = PermSudo(name=name.strip(), comment=comment, commands=commands.strip())
            sudo.save()
            msg = u"添加Sudo命令别名: %s" % name
        # 渲染数据

    return my_render('jperm/perm_sudo_add.html', locals(), request)


@require_role('admin')
def perm_sudo_edit(request):
    """
    list sudo commands alias
    :param request:
    :return:
    """
    # 渲染数据
    header_title, path1, path2 = "Sudo命令", "别名管理", "编辑别名"

    sudo_id = request.GET.get("id")
    sudo = PermSudo.objects.get(id=sudo_id)

    if request.method == "POST":
        name = request.POST.get("sudo_name")
        commands = request.POST.get("sudo_commands")
        comment = request.POST.get("sudo_comment")
        sudo.name = name.strip()
        sudo.commands = commands.strip()
        sudo.comment = comment
        sudo.save()

        msg = u"更新命令别名： %s" % name

    return my_render('jperm/perm_sudo_edit.html', locals(), request)


@require_role('admin')
def perm_sudo_delete(request):
    """
    list sudo commands alias
    :param request:
    :return:
    """
    if request.method == "POST":
        # 获取参数删除的role对象
        sudo_id = request.POST.get("id")
        sudo = PermSudo.objects.get(id=sudo_id)
        # 数据库里删除记录
        sudo.delete()
        return HttpResponse(u"删除角色: %s" % sudo.name)
    else:
        return HttpResponse(u"不支持该操作")


@require_role('admin')
def perm_role_recycle(request):
    role_id = request.GET.get('role_id')
    asset_ids = request.GET.get('asset_id').split(',')
    assets = []
    for asset_id in asset_ids:
        asset = get_object(Asset, id=asset_id)
        assets.append(asset)
        role = get_object(PermRole, id=role_id)
        PermPush.objects.filter(asset=asset, role=role).delete()

    res = gen_resource(assets)
    task = MyTask(res)

    return HttpResponse('删除成功')


@require_role('user')
def perm_role_get(request):
    asset_id = request.GET.get('id', 0)
    if asset_id:
        asset = get_object(Asset, id=asset_id)
        if asset:
            role = user_have_perm(request.user, asset=asset)
            return HttpResponse(','.join([i.name for i in role]))
    else:
        roles = get_group_user_perm(request.user).get('role').keys()
        return HttpResponse(','.join(i.name for i in roles))
    return HttpResponse('error')

