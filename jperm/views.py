# coding: utf-8

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from juser.models import User, UserGroup
from jasset.models import Asset, BisGroup
from jperm.models import Perm, SudoPerm, CmdGroup
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.db.models import Q
from jumpserver.views import LDAP_ENABLE, ldap_conn, CONF, perm_user_asset, page_list_return


if LDAP_ENABLE:
    LDAP_HOST_URL = CONF.get('ldap', 'host_url')
    LDAP_BASE_DN = CONF.get('ldap', 'base_dn')
    LDAP_ROOT_DN = CONF.get('ldap', 'root_dn')
    LDAP_ROOT_PW = CONF.get('ldap', 'root_pw')


def perm_group_update(user_group_name='', user_group_id='', asset_groups_name='', asset_groups_id=''):
    if user_group_name:
        user_group = UserGroup.objects.get(name=user_group_name)
    else:
        user_group = UserGroup.objects.get(id=user_group_id)

    Perm.objects.filter(user_group=user_group).delete()
    if asset_groups_name:
        for asset_group_name in asset_groups_name:
            asset_group = BisGroup.objects.get(name=asset_group_name)
            Perm(user_group=user_group, asset_group=asset_group).save()
    else:
        for asset_group_id in asset_groups_id:
            asset_group = BisGroup.objects.get(id=asset_group_id)
            Perm(user_group=user_group, asset_group=asset_group).save()


def perm_list(request):
    header_title, path1, path2 = u'主机授权 | Perm Host Detail.', u'授权管理', u'授权详情'
    groups = contact_list = Perm.objects.all()
    users = contact_list2 = User.objects.all().order_by('id')
    p = paginator = Paginator(contact_list, 10)
    try:
        current_page = int(request.GET.get('page', '1'))
    except ValueError:
        current_page = 1

    page_range = page_list_return(len(p.page_range), current_page)

    try:
        contacts = paginator.page(current_page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)
    return render_to_response('jperm/perm_list.html', locals(), context_instance=RequestContext(request))


def user_asset_cmd_groups_get(user_groups_select='', asset_groups_select='', cmd_groups_select=''):
    user_groups_select_list = []
    asset_groups_select_list = []
    cmd_groups_select_list = []

    for user_group_id in user_groups_select:
        user_groups_select_list.append(UserGroup.objects.get(id=user_group_id))

    for asset_group_id in asset_groups_select:
        asset_groups_select_list.append(BisGroup.objects.get(id=asset_group_id))

    for cmd_group_id in cmd_groups_select:
        cmd_groups_select_list.append(CmdGroup.objects.get(id=cmd_group_id))

    return user_groups_select_list, asset_groups_select_list, cmd_groups_select_list


def perm_add(request):
    header_title, path1, path2 = u'主机授权添加 | Perm Add Detail.', u'授权管理', u'授权添加'

    if request.method == 'GET':
        user_groups = UserGroup.objects.all()
        asset_groups = BisGroup.objects.all()

    else:
        name = request.POST.get('name', '')
        user_groups_select = request.POST.getlist('user_groups_select')
        asset_groups_select = request.POST.getlist('asset_groups_select')
        comment = request.POST.get('comment', '')

        user_groups, asset_groups = user_asset_cmd_groups_get(user_groups_select, asset_groups_select, '')[0:2]

        perm = Perm(name=name, comment=comment)
        perm.save()

        perm.user_group = user_groups
        perm.asset_group = asset_groups
        msg = '添加成功'
    return render_to_response('jperm/perm_add.html', locals(), context_instance=RequestContext(request))


def perm_list_ajax(request):
    tab = request.POST.get('tab', 'tab1')
    search = request.POST.get('search', '')

    if tab == 'tab1':
        groups = contact_list = UserGroup.objects.filter(name__icontains=search).order_by('type')
        p = paginator = Paginator(contact_list, 10)

        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        try:
            contacts = paginator.page(page)
        except (EmptyPage, InvalidPage):
            contacts = paginator.page(paginator.num_pages)

    else:
        users = contact_list2 = User.objects.filter(name__icontains=search).order_by('id')
        p2 = paginator2 = Paginator(contact_list2, 10)

        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        try:
            contacts2 = paginator2.page(page)
        except (EmptyPage, InvalidPage):
            contacts2 = paginator2.page(paginator2.num_pages)

    return render_to_response('jperm/perm_list_ajax.html', locals())


def perm_edit(request):
    if request.method == 'GET':
        header_title, path1, path2 = u'编辑授权 | Perm Host Edit.', u'授权管理', u'授权编辑'
        perm_id = request.GET.get('id')
        perm = Perm.objects.filter(id=perm_id)
        if perm:
            perm = perm[0]
            name = perm.name
            comment = perm.comment
            user_groups_select = perm.user_group.all()
            asset_groups_select = perm.asset_group.all()

            user_groups_all = UserGroup.objects.filter(Q(type='A') | Q(type='M'))
            asset_groups_all = BisGroup.objects.all()

            user_groups = [user_group for user_group in user_groups_all if user_group not in user_groups_select]
            asset_groups = [asset_group for asset_group in asset_groups_all if asset_group not in asset_groups_select]
    else:
        user_group_name = request.POST.get('user_group_name')
        asset_groups_selected = request.POST.getlist('asset_group_permed')
        perm_group_update(user_group_name=user_group_name, asset_groups_id=asset_groups_selected)
        return HttpResponseRedirect('/jperm/perm_list/', locals(), context_instance=RequestContext(request))
    return render_to_response('jperm/perm_edit.html', locals(), context_instance=RequestContext(request))


def perm_detail(request):
    header_title, path1, path2 = u'编辑授权 | Perm Host Edit.', u'授权管理', u'授权详情'
    perm_id = request.GET.get('id')
    perm = Perm.objects.filter(id=perm_id)
    if perm:
        perm = perm[0]
        user_groups = perm.user_group.all()
        asset_groups = perm.asset_group.all()

        users_list = []
        assets_list = []

        for user_group in user_groups:
            users_list.extend(user_group.user_set.all())
        for asset_group in asset_groups:
            assets_list.extend(asset_group.asset_set.all())

    return render_to_response('jperm/perm_detail.html', locals(), context_instance=RequestContext(request))


def perm_del(request):
    perm_id = request.GET.get('id')
    perm = Perm.objects.filter(id=perm_id)
    if perm:
        perm = perm[0]
        perm.delete()
    return HttpResponseRedirect('/jperm/perm_list/')


def perm_asset_detail(request):
    header_title, path1, path2 = u'用户授权主机 | User Perm Asset.', u'权限管理', u'用户主机详情'
    user_id = request.GET.get('id')
    user = User.objects.filter(id=user_id)
    if user:
        user = user[0]
        assets_list = perm_user_asset(user_id)
    return render_to_response('jperm/perm_asset_detail.html', locals(), context_instance=RequestContext(request))


def sudo_db_add(name, user_runas, user_groups_select, asset_groups_select, cmd_groups_select, comment):
    user_groups_select_list, asset_groups_select_list, cmd_groups_select_list = \
        user_asset_cmd_groups_get(user_groups_select, asset_groups_select, cmd_groups_select)

    sudo_perm = SudoPerm(name=name, user_runas=user_runas, comment=comment)
    sudo_perm.save()
    sudo_perm.user_group = user_groups_select_list
    sudo_perm.asset_group = asset_groups_select_list
    sudo_perm.cmd_group = cmd_groups_select_list


def sudo_db_update(sudo_perm_id, name, user_runas, user_groups_select, asset_groups_select, cmd_groups_select, comment):
    user_groups_select_list, asset_groups_select_list, cmd_groups_select_list = \
        user_asset_cmd_groups_get(user_groups_select, asset_groups_select, cmd_groups_select)
    sudo_perm = SudoPerm.objects.filter(id=sudo_perm_id)
    if sudo_perm:
        sudo_perm.update(name=name, user_runas=user_runas, comment=comment)
        sudo_perm = sudo_perm[0]
        sudo_perm.user_group = user_groups_select_list
        sudo_perm.asset_group = asset_groups_select_list
        sudo_perm.cmd_group = cmd_groups_select_list


def unicode2str(unicode_list):
    return [str(i) for i in unicode_list]


def sudo_ldap_add(name, users_runas, user_groups_select, asset_groups_select,
                  cmd_groups_select, update=False, old_name=''):
    user_groups_select_list, asset_groups_select_list, cmd_groups_select_list = \
        user_asset_cmd_groups_get(user_groups_select, asset_groups_select, cmd_groups_select)

    users = []
    assets = []
    cmds = []
    users_runas = users_runas.split(',')
    asset_all = False

    for user_group in user_groups_select_list:
        users.extend(user_group.user_set.all())

    for asset_group in asset_groups_select_list:
        if u'ALL' in asset_group.name:
            asset_all = True
            break
        else:
            assets.extend(asset_group.asset_set.all())

    for cmd_group in cmd_groups_select_list:
        cmds.extend(cmd_group.cmd.split(','))

    users_name = [user.username for user in users]
    if asset_all:
        assets_ip = ['ALL']
    else:
        assets_ip = [asset.ip for asset in assets]

    sudo_dn = 'cn=%s,ou=Sudoers,%s' % (name, LDAP_BASE_DN)
    sudo_attr = {'objectClass': ['top', 'sudoRole'],
                 'cn': ['%s' % str(name)],
                 'sudoCommand': unicode2str(cmds),
                 'sudoHost': unicode2str(assets_ip),
                 'sudoOption': ['!authenticate'],
                 'sudoRunAsUser': unicode2str(users_runas),
                 'sudoUser': unicode2str(users_name)}

    if update:
        old_sudo_dn = 'cn=%s,ou=Sudoers,%s' % (old_name, LDAP_BASE_DN)
        ldap_conn.delete(old_sudo_dn)

    ldap_conn.add(sudo_dn, sudo_attr)


def sudo_add(request):
    header_title, path1, path2 = u'Sudo授权 | Perm Sudo Add.', u'权限管理', u'添加Sudo权限'
    user_groups = UserGroup.objects.all()
    asset_groups = BisGroup.objects.all()
    cmd_groups = CmdGroup.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name')
        users_runas = request.POST.get('runas', 'root')
        user_groups_select = request.POST.getlist('user_groups_select')
        asset_groups_select = request.POST.getlist('asset_groups_select')
        cmd_groups_select = request.POST.getlist('cmd_groups_select')
        comment = request.POST.get('comment', '')

        sudo_db_add(name, users_runas, user_groups_select, asset_groups_select, cmd_groups_select, comment)
        sudo_ldap_add(name, users_runas, user_groups_select, asset_groups_select, cmd_groups_select)

        msg = '添加成功'
        return HttpResponseRedirect('/jperm/sudo_list/')
    return render_to_response('jperm/sudo_add.html', locals(), context_instance=RequestContext(request))


def sudo_list(request):
    header_title, path1, path2 = u'Sudo授权 | Perm Sudo Detail.', u'权限管理', u'Sudo权限详情'
    sudo_perms = contact_list = SudoPerm.objects.all()
    p1 = paginator1 = Paginator(contact_list, 10)
    user_groups = UserGroup.objects.filter(Q(type='A') | Q(type='P'))
    asset_groups = BisGroup.objects.all()
    cmd_groups = CmdGroup.objects.all()

    try:
        page1 = int(request.GET.get('page', '1'))
    except ValueError:
        page1 = 1

    try:
        contacts1 = paginator1.page(page1)
    except (EmptyPage, InvalidPage):
        contacts1 = paginator1.page(paginator1.num_pages)
    return render_to_response('jperm/sudo_list.html', locals(), context_instance=RequestContext(request))


def sudo_edit(request):
    header_title, path1, path2 = u'Sudo授权 | Perm Sudo Detail.', u'授权管理', u'Sudo修改'

    if request.method == 'GET':
        sudo_perm_id = request.GET.get('id', '0')
        sudo_perm = SudoPerm.objects.filter(id=int(sudo_perm_id))
        if sudo_perm:
            user_group_all = UserGroup.objects.filter(Q(type='A') | Q(type='P'))
            asset_group_all = BisGroup.objects.filter()
            cmd_group_all = CmdGroup.objects.all()

            sudo_perm = sudo_perm[0]
            user_group_permed = sudo_perm.user_group.all()
            asset_group_permed = sudo_perm.asset_group.all()
            cmd_group_permed = sudo_perm.cmd_group.all()

            user_groups = [user_group for user_group in user_group_all if user_group not in user_group_permed]
            asset_groups = [asset_group for asset_group in asset_group_all if asset_group not in asset_group_permed]
            cmd_groups = [cmd_group for cmd_group in cmd_group_all if cmd_group not in cmd_group_permed]

            name = sudo_perm.name
            user_runas = sudo_perm.user_runas
            comment = sudo_perm.comment

    else:
        sudo_perm_id = request.POST.get('sudo_perm_id')
        name = request.POST.get('name')
        users_runas = request.POST.get('runas', 'root')
        user_groups_select = request.POST.getlist('user_groups_select')
        asset_groups_select = request.POST.getlist('asset_groups_select')
        cmd_groups_select = request.POST.getlist('cmd_groups_select')
        comment = request.POST.get('comment', '')

        sudo_perm = SudoPerm.objects.get(id=sudo_perm_id)
        old_name = sudo_perm.name
        sudo_db_update(sudo_perm_id, name, users_runas, user_groups_select,
                       asset_groups_select, cmd_groups_select, comment)
        sudo_ldap_add(name, users_runas, user_groups_select, asset_groups_select,
                      cmd_groups_select, update=True, old_name=str(old_name))
        msg = '修改成功'

        return HttpResponseRedirect('/jperm/sudo_list/')

    return render_to_response('jperm/sudo_edit.html', locals(), context_instance=RequestContext(request))


def sudo_detail(request):
    header_title, path1, path2 = u'Sudo授权详情 | Perm Sudo Detail.', u'授权管理', u'授权详情'
    sudo_perm_id = request.GET.get('id')
    sudo_perm = SudoPerm.objects.filter(id=sudo_perm_id)
    if sudo_perm:
        sudo_perm = sudo_perm[0]
        user_groups = sudo_perm.user_group.all()
        asset_groups = sudo_perm.asset_group.all()
        cmd_groups = sudo_perm.cmd_group.all()

        users_list = []
        assets_list = []
        cmds_list = []

        for user_group in user_groups:
            users_list.extend(user_group.user_set.all())
        for asset_group in asset_groups:
            assets_list.extend(asset_group.asset_set.all())
        for cmd_group in cmd_groups:
            cmds_list.append({cmd_group.name: cmd_group.cmd.split(',')})

        return render_to_response('jperm/sudo_detail.html', locals(), context_instance=RequestContext(request))


def sudo_del(request):
    sudo_perm_id = request.GET.get('id', '0')
    sudo_perm = SudoPerm.objects.filter(id=int(sudo_perm_id))
    if sudo_perm:
        name = sudo_perm[0].name
        sudo_perm.delete()
        sudo_dn = 'cn=%s,ou=Sudoers,%s' % (name, LDAP_BASE_DN)
        ldap_conn.delete(sudo_dn)
    return HttpResponseRedirect('/jperm/sudo_list/')


def cmd_add(request):
    header_title, path1, path2 = u'sudo命令添加 | Sudo Cmd Add.', u'授权管理管理', u'命令组添加'

    if request.method == 'POST':
        name = request.POST.get('name')
        cmd = ','.join(request.POST.get('cmd').split())
        comment = request.POST.get('comment')

        CmdGroup.objects.create(name=name, cmd=cmd, comment=comment)
        msg = u'命令组添加成功'

        return HttpResponseRedirect('/jperm/cmd_list/')

    return render_to_response('jperm/sudo_cmd_add.html', locals(), context_instance=RequestContext(request))


def cmd_edit(request):
    header_title, path1, path2 = u'sudo命令修改 | Sudo Cmd Edit.', u'授权管理管理', u'命令组修改'

    cmd_group_id = request.GET.get('id')
    cmd_group = CmdGroup.objects.filter(id=cmd_group_id)

    if cmd_group:
        cmd_group = cmd_group[0]
        cmd_group_id = cmd_group.id
        name = cmd_group.name
        cmd = cmd_group.cmd
        comment = cmd_group.comment

    if request.method == 'POST':
        cmd_group_id = request.POST.get('cmd_group_id')
        name = request.POST.get('name')
        cmd = ','.join(request.POST.get('cmd').split())
        comment = request.POST.get('comment')

        cmd_group = CmdGroup.objects.filter(id=cmd_group_id)
        if cmd_group:
            cmd_group.update(name=name, cmd=cmd, comment=comment)
            return HttpResponseRedirect('/jperm/cmd_list/')
    return render_to_response('jperm/sudo_cmd_add.html', locals(), context_instance=RequestContext(request))


def cmd_list(request):
    header_title, path1, path2 = u'sudo命令查看 | Sudo Cmd List.', u'权限管理', u'Sudo命令添加'

    cmd_groups = contact_list = CmdGroup.objects.all()
    p = paginator = Paginator(contact_list, 10)

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        contacts = paginator.page(page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)
    return render_to_response('jperm/sudo_cmd_list.html', locals(), context_instance=RequestContext(request))


def cmd_del(request):
    cmd_group_id = request.GET.get('id')
    cmd_group = CmdGroup.objects.filter(id=cmd_group_id)

    if cmd_group:
        cmd_group[0].delete()
    return HttpResponseRedirect('/jperm/cmd_list/')
