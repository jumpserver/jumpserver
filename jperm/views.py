# coding: utf-8
import sys

reload(sys)
sys.setdefaultencoding('utf8')

from django.shortcuts import render_to_response
from django.template import RequestContext
from jperm.models import Perm, SudoPerm, CmdGroup, Apply
from django.db.models import Q
from jumpserver.api import *


def asset_cmd_groups_get(asset_groups_select='', cmd_groups_select=''):
    asset_groups_select_list = []
    cmd_groups_select_list = []

    for asset_group_id in asset_groups_select:
        asset_groups_select_list.extend(BisGroup.objects.filter(id=asset_group_id))

    for cmd_group_id in cmd_groups_select:
        cmd_groups_select_list.extend(CmdGroup.objects.filter(id=cmd_group_id))

    return asset_groups_select_list, cmd_groups_select_list


@require_admin
def perm_add(request):
    header_title, path1, path2 = u'主机授权添加', u'授权管理', u'授权添加'

    if request.method == 'GET':
        user_groups = UserGroup.objects.filter(id__gt=2)
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


def dept_add_asset(dept_id, asset_list):
    dept = DEPT.objects.filter(id=dept_id)
    if dept:
        dept = dept[0]
        new_perm_asset = []
        for asset_id in asset_list:
            asset = Asset.objects.filter(id=asset_id)
            new_perm_asset.extend(asset)

        dept.asset_set.clear()
        dept.asset_set = new_perm_asset


@require_super_user
def dept_perm_edit(request):
    header_title, path1, path2 = u'部门授权添加', u'授权管理', u'部门授权添加'
    if request.method == 'GET':
        dept_id = request.GET.get('id', '')
        dept = DEPT.objects.filter(id=dept_id)
        if dept:
            dept = dept[0]
            asset_all = Asset.objects.all()
            asset_select = dept.asset_set.all()
            assets = [asset for asset in asset_all if asset not in asset_select]
    else:
        dept_id = request.POST.get('dept_id')
        asset_select = request.POST.getlist('asset_select')
        dept_add_asset(dept_id, asset_select)
        return HttpResponseRedirect('/jperm/dept_perm_list/')
    return render_to_response('jperm/dept_perm_edit.html', locals(), context_instance=RequestContext(request))


@require_super_user
def perm_list(request):
    header_title, path1, path2 = u'小组授权', u'授权管理', u'授权详情'
    keyword = request.GET.get('search', '')
    uid = request.GET.get('uid', '')
    agid = request.GET.get('agid', '')
    if keyword:
        contact_list = UserGroup.objects.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword))
    else:
        contact_list = UserGroup.objects.all().order_by('name')

    if uid:
        user = User.objects.filter(id=uid)
        print user
        if user:
            user = user[0]
            contact_list = contact_list.filter(user=user)

    if agid:
        contact_list_confirm = []
        asset_group = BisGroup.objects.filter(id=agid)
        if asset_group:
            asset_group = asset_group[0]
            for user_group in contact_list:
                if asset_group in user_group_perm_asset_group_api(user_group):
                    contact_list_confirm.append(user_group)
            contact_list = contact_list_confirm

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)
    return render_to_response('jperm/perm_list.html', locals(), context_instance=RequestContext(request))


@require_admin
def perm_list_adm(request):
    header_title, path1, path2 = u'小组授权', u'授权管理', u'授权详情'
    keyword = request.GET.get('search', '')
    uid = request.GET.get('uid', '')
    agid = request.GET.get('agid', '')
    user, dept = get_session_user_dept(request)
    contact_list = dept.usergroup_set.all().order_by('name')
    if keyword:
        contact_list = contact_list.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword))

    if uid:
        user = User.objects.filter(id=uid)
        print user
        if user:
            user = user[0]
            contact_list = contact_list.filter(user=user)

    if agid:
        contact_list_confirm = []
        asset_group = BisGroup.objects.filter(id=agid)
        if asset_group:
            asset_group = asset_group[0]
            for user_group in contact_list:
                if asset_group in user_group_perm_asset_group_api(user_group):
                    contact_list_confirm.append(user_group)
            contact_list = contact_list_confirm

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)
    return render_to_response('jperm/perm_list.html', locals(), context_instance=RequestContext(request))


@require_super_user
def dept_perm_list(request):
    header_title, path1, path2 = '查看部门', '授权管理', '部门授权'
    keyword = request.GET.get('search')
    if keyword:
        contact_list = DEPT.objects.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword)).order_by('name')
    else:
        contact_list = DEPT.objects.filter(id__gt=2)

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)

    return render_to_response('jperm/dept_perm_list.html', locals(), context_instance=RequestContext(request))


def perm_group_update(user_group_id, asset_groups_id_list):
    user_group = UserGroup.objects.filter(id=user_group_id)
    if user_group:
        user_group = user_group[0]
        old_asset_group = [perm.asset_group for perm in user_group.perm_set.all()]
        new_asset_group = []

        for asset_group_id in asset_groups_id_list:
            new_asset_group.extend(BisGroup.objects.filter(id=asset_group_id))

        del_asset_group = [asset_group for asset_group in old_asset_group if asset_group not in new_asset_group]
        add_asset_group = [asset_group for asset_group in new_asset_group if asset_group not in old_asset_group]

        for asset_group in del_asset_group:
            Perm.objects.filter(user_group=user_group, asset_group=asset_group).delete()

        for asset_group in add_asset_group:
            Perm(user_group=user_group, asset_group=asset_group).save()


@require_super_user
def perm_edit(request):
    if request.method == 'GET':
        header_title, path1, path2 = u'编辑授权', u'授权管理', u'授权编辑'
        user_group_id = request.GET.get('id', '')
        user_group = UserGroup.objects.filter(id=user_group_id)
        if user_group:
            user_group = user_group[0]
            asset_groups_all = BisGroup.objects.all()
            asset_groups_select = [perm.asset_group for perm in user_group.perm_set.all()]
            asset_groups = [asset_group for asset_group in asset_groups_all if asset_group not in asset_groups_select]
    else:
        user_group_id = request.POST.get('user_group_id')
        asset_group_id_list = request.POST.getlist('asset_groups_select')
        perm_group_update(user_group_id, asset_group_id_list)

        return HttpResponseRedirect('/jperm/perm_list/')
    return render_to_response('jperm/perm_edit.html', locals(), context_instance=RequestContext(request))


@require_admin
def perm_edit_adm(request):
    if request.method == 'GET':
        header_title, path1, path2 = u'编辑授权', u'授权管理', u'授权编辑'
        user_group_id = request.GET.get('id', '')
        user_group = UserGroup.objects.filter(id=user_group_id)
        user, dept = get_session_user_dept(request)
        if user_group:
            user_group = user_group[0]
            asset_groups_all = dept.bisgroup_set.all()
            asset_groups_select = [perm.asset_group for perm in user_group.perm_set.all()]
            asset_groups = [asset_group for asset_group in asset_groups_all if asset_group not in asset_groups_select]
    else:
        user_group_id = request.POST.get('user_group_id')
        asset_group_id_list = request.POST.getlist('asset_groups_select')
        print user_group_id, asset_group_id_list
        if not validate(request, user_group=[user_group_id], asset_group=asset_group_id_list):
            return HttpResponseRedirect('/')
        perm_group_update(user_group_id, asset_group_id_list)

        return HttpResponseRedirect('/jperm/perm_list/')
    return render_to_response('jperm/perm_edit.html', locals(), context_instance=RequestContext(request))


@require_admin
def perm_detail(request):
    header_title, path1, path2 = u'授权管理', u'小组管理', u'授权详情'
    group_id = request.GET.get('id')
    user_group = UserGroup.objects.filter(id=group_id)
    if user_group:
        user_group = user_group[0]
        users = user_group.user_set.all()
        group_user_num = len(users)
        perms = user_group.perm_set.all()
        asset_groups = [perm.asset_group for perm in perms]
    return render_to_response('jperm/perm_detail.html', locals(), context_instance=RequestContext(request))


@require_admin
def perm_del(request):
    perm_id = request.GET.get('id')
    perm = Perm.objects.filter(id=perm_id)
    if perm:
        perm = perm[0]
        perm.delete()
    return HttpResponseRedirect('/jperm/perm_list/')


@require_admin
def perm_asset_detail(request):
    header_title, path1, path2 = u'用户授权主机', u'权限管理', u'用户主机详情'
    user_id = request.GET.get('id')
    user = User.objects.filter(id=user_id)
    if user:
        user = user[0]
        assets_list = user_perm_asset_api(user.username)
    return render_to_response('jperm/perm_asset_detail.html', locals(), context_instance=RequestContext(request))


def unicode2str(unicode_list):
    return [str(i) for i in unicode_list]


def sudo_ldap_add(user_group, user_runas, asset_groups_select,
                  cmd_groups_select):
    if LDAP_ENABLE:
        ldap_conn = LDAPMgmt(LDAP_HOST_URL, LDAP_BASE_DN, LDAP_ROOT_DN, LDAP_ROOT_PW)
    else:
        return

    assets = []
    cmds = []
    user_runas = user_runas.split(',')
    if len(asset_groups_select) == 1 and asset_groups_select[0].name == 'ALL':
        asset_all = True
    else:
        asset_all = False
        for asset_group in asset_groups_select:
            assets.extend(asset_group.asset_set.all())

    if user_group.name == 'ALL':
        user_all = True
        users = []
    else:
        user_all = False
        users = user_group.user_set.all()

    for cmd_group in cmd_groups_select:
        cmds.extend(cmd_group.cmd.split(','))

    if user_all:
        users_name = ['ALL']
    else:
        users_name = list(set([user.username for user in users]))

    if asset_all:
        assets_ip = ['ALL']
    else:
        assets_ip = list(set([asset.ip for asset in assets]))

    name = 'sudo%s' % user_group.id
    sudo_dn = 'cn=%s,ou=Sudoers,%s' % (name, LDAP_BASE_DN)
    sudo_attr = {'objectClass': ['top', 'sudoRole'],
                 'cn': ['%s' % name],
                 'sudoCommand': unicode2str(cmds),
                 'sudoHost': unicode2str(assets_ip),
                 'sudoOption': ['!authenticate'],
                 'sudoRunAsUser': unicode2str(user_runas),
                 'sudoUser': unicode2str(users_name)}
    ldap_conn.delete(sudo_dn)
    ldap_conn.add(sudo_dn, sudo_attr)


def sudo_update(user_group, user_runas, asset_groups_select, cmd_groups_select, comment):
    asset_groups_select_list, cmd_groups_select_list = \
        asset_cmd_groups_get(asset_groups_select, cmd_groups_select)
    sudo_perm = user_group.sudoperm_set.all()
    if sudo_perm:
        sudo_perm.update(user_runas=user_runas, comment=comment)
        sudo_perm = sudo_perm[0]
        sudo_perm.asset_group = asset_groups_select_list
        sudo_perm.cmd_group = cmd_groups_select_list
    else:
        sudo_perm = SudoPerm(user_group=user_group, user_runas=user_runas, comment=comment)
        sudo_perm.save()
        sudo_perm.asset_group = asset_groups_select_list
        sudo_perm.cmd_group = cmd_groups_select_list

    sudo_ldap_add(user_group, user_runas, asset_groups_select_list, cmd_groups_select_list)


@require_super_user
def sudo_list(request):
    header_title, path1, path2 = u'Sudo授权', u'权限管理', u'Sudo权限详情'
    keyword = request.GET.get('search', '')
    contact_list = UserGroup.objects.all().order_by('name')
    if keyword:
        contact_list = contact_list.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword))

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)
    return render_to_response('jperm/sudo_list.html', locals(), context_instance=RequestContext(request))


@require_admin
def sudo_list_adm(request):
    header_title, path1, path2 = u'Sudo授权', u'权限管理', u'Sudo权限详情'
    keyword = request.GET.get('search', '')
    user, dept = get_session_user_dept(request)
    contact_list = dept.usergroup_set.all().order_by('name')
    if keyword:
        contact_list = contact_list.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword))

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)
    return render_to_response('jperm/sudo_list.html', locals(), context_instance=RequestContext(request))


@require_super_user
def sudo_edit(request):
    header_title, path1, path2 = u'Sudo授权', u'授权管理', u'Sudo授权'

    if request.method == 'GET':
        user_group_id = request.GET.get('id', '0')
        user_group = UserGroup.objects.filter(id=user_group_id)
        asset_group_all = BisGroup.objects.filter()
        cmd_group_all = CmdGroup.objects.all()
        if user_group:
            user_group = user_group[0]
            sudo_perm = user_group.sudoperm_set.all()
            if sudo_perm:
                sudo_perm = sudo_perm[0]
                asset_group_permed = sudo_perm.asset_group.all()
                cmd_group_permed = sudo_perm.cmd_group.all()
                user_runas = sudo_perm.user_runas
                comment = sudo_perm.comment
            else:
                asset_group_permed = []
                cmd_group_permed = []

            asset_groups = [asset_group for asset_group in asset_group_all if asset_group not in asset_group_permed]
            cmd_groups = [cmd_group for cmd_group in cmd_group_all if cmd_group not in cmd_group_permed]

    else:
        user_group_id = request.POST.get('user_group_id', '')
        users_runas = request.POST.get('runas') if request.POST.get('runas') else 'root'
        asset_groups_select = request.POST.getlist('asset_groups_select')
        cmd_groups_select = request.POST.getlist('cmd_groups_select')
        comment = request.POST.get('comment', '')
        user_group = UserGroup.objects.filter(id=user_group_id)
        if user_group:
            user_group = user_group[0]
            if LDAP_ENABLE:
                sudo_update(user_group, users_runas, asset_groups_select, cmd_groups_select, comment)
                msg = '修改成功'

        return HttpResponseRedirect('/jperm/sudo_list/')

    return render_to_response('jperm/sudo_edit.html', locals(), context_instance=RequestContext(request))


@require_admin
def sudo_edit_adm(request):
    header_title, path1, path2 = u'Sudo授权', u'授权管理', u'Sudo授权'
    user, dept = get_session_user_dept(request)
    if request.method == 'GET':
        user_group_id = request.GET.get('id', '0')
        if not validate(request, user_group=[user_group_id]):
            return render_to_response('/jperm/sudo_list/')
        user_group = UserGroup.objects.filter(id=user_group_id)
        asset_group_all = dept.bisgroup_set.all()
        cmd_group_all = dept.cmdgroup_set.all()
        if user_group:
            user_group = user_group[0]
            sudo_perm = user_group.sudoperm_set.all()
            if sudo_perm:
                sudo_perm = sudo_perm[0]
                asset_group_permed = sudo_perm.asset_group.all()
                cmd_group_permed = sudo_perm.cmd_group.all()
                user_runas = sudo_perm.user_runas
                comment = sudo_perm.comment
            else:
                asset_group_permed = []
                cmd_group_permed = []

            asset_groups = [asset_group for asset_group in asset_group_all if asset_group not in asset_group_permed]
            cmd_groups = [cmd_group for cmd_group in cmd_group_all if cmd_group not in cmd_group_permed]

    else:
        user_group_id = request.POST.get('user_group_id', '')
        users_runas = request.POST.get('runas', 'root')
        asset_groups_select = request.POST.getlist('asset_groups_select')
        cmd_groups_select = request.POST.getlist('cmd_groups_select')
        comment = request.POST.get('comment', '')
        user_group = UserGroup.objects.filter(id=user_group_id)
        if not validate(request, user_group=[user_group_id], asset_group=asset_groups_select):
            return render_to_response('/jperm/sudo_list/')
        if user_group:
            user_group = user_group[0]
            if LDAP_ENABLE:
                sudo_update(user_group, users_runas, asset_groups_select, cmd_groups_select, comment)
                msg = '修改成功'

        return HttpResponseRedirect('/jperm/sudo_list/')
    return render_to_response('jperm/sudo_edit.html', locals(), context_instance=RequestContext(request))


@require_admin
def sudo_detail(request):
    header_title, path1, path2 = u'Sudo授权详情', u'授权管理', u'授权详情'
    user_group_id = request.GET.get('id')
    user_group = UserGroup.objects.filter(id=user_group_id)
    if user_group:
        asset_groups = []
        cmd_groups = []
        user_group = user_group[0]
        users = user_group.user_set.all()
        group_user_num = len(users)

        for perm in user_group.sudoperm_set.all():
            asset_groups.extend(perm.asset_group.all())
            cmd_groups.extend(perm.cmd_group.all())

        print asset_groups
    return render_to_response('jperm/sudo_detail.html', locals(), context_instance=RequestContext(request))


@require_admin
def sudo_refresh(request):
    sudo_perm_all = SudoPerm.objects.all()
    for sudo_perm in sudo_perm_all:
        user_group = sudo_perm.user_group
        user_runas = sudo_perm.user_runas
        asset_groups_select = sudo_perm.asset_group.all()
        cmd_groups_select = sudo_perm.cmd_group.all()
        sudo_ldap_add(user_group, user_runas, asset_groups_select, cmd_groups_select)
    return HttpResponse('刷新sudo授权成功')


@require_super_user
def cmd_add(request):
    header_title, path1, path2 = u'sudo命令添加', u'授权管理', u'命令组添加'
    dept_all = DEPT.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name')
        dept_id = request.POST.get('dept_id')
        cmd = ','.join(request.POST.get('cmd').splitlines())
        comment = request.POST.get('comment')
        dept = DEPT.objects.filter(id=dept_id)

        try:
            if CmdGroup.objects.filter(name=name):
                error = '%s 命令组已存在'
                raise ServerError(error)

            if not dept:
                error = u"部门不能为空"
                raise ServerError(error)
        except ServerError, e:
            pass
        else:
            dept = dept[0]
            CmdGroup.objects.create(name=name, dept=dept, cmd=cmd, comment=comment)
            msg = u'命令组添加成功'
            return HttpResponseRedirect('/jperm/cmd_list/')

    return render_to_response('jperm/sudo_cmd_add.html', locals(), context_instance=RequestContext(request))


@require_admin
def cmd_add_adm(request):
    header_title, path1, path2 = u'sudo命令添加', u'授权管理', u'命令组添加'
    user, dept = get_session_user_dept(request)

    if request.method == 'POST':
        name = request.POST.get('name')
        cmd = ','.join(request.POST.get('cmd').splitlines())
        comment = request.POST.get('comment')

        try:
            if CmdGroup.objects.filter(name=name):
                error = '%s 命令组已存在'
                raise ServerError(error)
        except ServerError, e:
            pass
        else:
            CmdGroup.objects.create(name=name, dept=dept, cmd=cmd, comment=comment)
            return HttpResponseRedirect('/jperm/cmd_list/')

        return HttpResponseRedirect('/jperm/cmd_list/')

    return render_to_response('jperm/sudo_cmd_add.html', locals(), context_instance=RequestContext(request))


@require_admin
def cmd_edit(request):
    header_title, path1, path2 = u'sudo命令修改', u'授权管理管理', u'命令组修改'

    cmd_group_id = request.GET.get('id')
    cmd_group = CmdGroup.objects.filter(id=cmd_group_id)
    dept_all = DEPT.objects.all()

    if cmd_group:
        cmd_group = cmd_group[0]
        cmd_group_id = cmd_group.id
        dept_id = cmd_group.dept.id
        name = cmd_group.name
        cmd = '\n'.join(cmd_group.cmd.split(','))
        comment = cmd_group.comment

    if request.method == 'POST':
        cmd_group_id = request.POST.get('cmd_group_id')
        name = request.POST.get('name')
        dept_id = request.POST.get('dept_id')
        cmd = ','.join(request.POST.get('cmd').splitlines())
        comment = request.POST.get('comment')
        cmd_group = CmdGroup.objects.filter(id=cmd_group_id)

        dept = DEPT.objects.filter(id=dept_id)
        try:
            if not dept:
                error = '没有该部门'
                raise ServerError(error)

            if not cmd_group:
                error = '没有该命令组'
        except ServerError, e:
            pass
        else:
            cmd_group.update(name=name, cmd=cmd, dept=dept[0], comment=comment)
            return HttpResponseRedirect('/jperm/cmd_list/')
    return render_to_response('jperm/sudo_cmd_add.html', locals(), context_instance=RequestContext(request))


@require_admin
def cmd_list(request):
    header_title, path1, path2 = u'sudo命令查看', u'权限管理', u'Sudo命令添加'

    if is_super_user(request):
        cmd_groups = contact_list = CmdGroup.objects.all()
    else:
        user, dept = get_session_user_dept(request)
        cmd_groups = contact_list = dept.cmdgroup_set.all()
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


@require_admin
def cmd_del(request):
    cmd_group_id = request.GET.get('id')
    cmd_group = CmdGroup.objects.filter(id=cmd_group_id)

    if cmd_group:
        cmd_group[0].delete()
    return HttpResponseRedirect('/jperm/cmd_list/')


@require_admin
def cmd_detail(request):
    cmd_ids = request.GET.get('id').split(',')
    cmds = []
    if len(cmd_ids) == 1:
        if cmd_ids[0]:
            cmd_id = cmd_ids[0]
        else:
            cmd_id = 1
        cmd_group = CmdGroup.objects.filter(id=cmd_id)
        if cmd_group:
            cmd_group = cmd_group[0]
            cmds.extend(cmd_group.cmd.split(','))
            cmd_group_name = cmd_group.name
    else:
        cmd_groups = []
        for cmd_id in cmd_ids:
            cmd_groups.extend(CmdGroup.objects.filter(id=cmd_id))
        for cmd_group in cmd_groups:
            cmds.extend(cmd_group.cmd.split(','))

    cmds_str = ', '.join(cmds)

    return render_to_response('jperm/sudo_cmd_detail.html', locals(), context_instance=RequestContext(request))


@require_login
def perm_apply(request):
    """ 权限申请 """
    header_title, path1, path2 = u'主机权限申请', u'权限管理', u'申请主机'
    user_id, username = get_session_user_info(request)[0:2]
    name = User.objects.get(id=user_id).username
    dept_id, deptname, dept = get_session_user_info(request)[3:6]
    perm_host = user_perm_asset_api(username)
    all_host = Asset.objects.filter(dept=dept)

    perm_group = user_perm_group_api(username)
    all_group = dept.bisgroup_set.all()

    posts = [g for g in all_host if g not in perm_host]
    egroup = [d for d in all_group if d not in perm_group]

    dept_da = User.objects.filter(dept_id=dept_id, role='DA')
    admin = User.objects.get(name='admin')

    if request.method == 'POST':
        applyer = request.POST.get('applyer')
        dept = request.POST.get('dept')
        da = request.POST.get('da')
        group = request.POST.getlist('group')
        hosts = request.POST.getlist('hosts')
        comment = request.POST.get('comment')
        if not da:
            return httperror(request, u'请选择管理员!')
        da = User.objects.get(id=da)
        mail_address = da.email
        mail_title = '%s - 权限申请' % username
        group_lis = ', '.join(group)
        hosts_lis = ', '.join(hosts)
        time_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        a = Apply.objects.create(applyer=applyer, admin=da, dept=dept, bisgroup=group, date_add=datetime.datetime.now(),
                                 asset=hosts, status=0, comment=comment, read=0)
        uuid = a.uuid
        url = "http://%s:%s/jperm/apply_exec/?uuid=%s" % (SEND_IP, SEND_PORT, uuid)
        mail_msg = """
        Hi,%s:
            有新的权限申请, 详情如下:
                申请人: %s
                申请主机组: %s
                申请的主机: %s
                申请时间: %s
                申请说明: %s
            请及时审批, 审批完成后, 点击以下链接或登录授权管理-权限审批页面点击确认键,告知申请人。

            %s
        """ % (da.username, applyer, group_lis, hosts_lis, time_now, comment, url)

        send_mail(mail_title, mail_msg, MAIL_FROM, [mail_address], fail_silently=False)
        smg = "提交成功,已发邮件至 %s 通知部门管理员。" % mail_address
        return render_to_response('jperm/perm_apply.html', locals(), context_instance=RequestContext(request))
    return render_to_response('jperm/perm_apply.html', locals(), context_instance=RequestContext(request))


@require_admin
def perm_apply_exec(request):
    """ 确认权限 """
    header_title, path1, path2 = u'主机权限申请', u'权限管理', u'审批完成'
    uuid = request.GET.get('uuid')
    user_id = request.session.get('user_id')
    approver = User.objects.get(id=user_id).name
    if uuid:
        p_apply = Apply.objects.filter(uuid=str(uuid))
        q_apply = Apply.objects.get(uuid=str(uuid))
        if q_apply.status == 1:
            smg = '此权限已经审批完成, 请勿重复审批, 十秒钟后返回首页'
            return render_to_response('jperm/perm_apply_exec.html', locals(), context_instance=RequestContext(request))
        else:
            user = User.objects.get(username=q_apply.applyer)
            mail_address = user.email
            time_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            p_apply.update(status=1, approver=approver, date_end=time_now)
            mail_title = '%s - 权限审批完成' % q_apply.applyer
            mail_msg = """
            Hi,%s:
                您所申请的权限已由 %s 在 %s 审批完成, 请登录验证。
            """ % (q_apply.applyer, q_apply.approver, time_now)
            send_mail(mail_title, mail_msg, MAIL_FROM, [mail_address], fail_silently=False)
            smg = '授权完成, 已邮件通知申请人, 十秒钟后返回首页'
            return render_to_response('jperm/perm_apply_exec.html', locals(), context_instance=RequestContext(request))
    else:
        smg = '没有此授权记录, 十秒钟后返回首页'
        return render_to_response('jperm/perm_apply_exec.html', locals(), context_instance=RequestContext(request))


def get_apply_posts(request, status, username, dept_name, keyword=None):
    """ 获取申请记录 """
    post_all = Apply.objects.filter(status=status).order_by('-date_add')
    post_keyword_all = Apply.objects.filter(Q(applyer__contains=keyword) |
                                            Q(approver__contains=keyword)) \
        .filter(status=status).order_by('-date_add')

    if is_super_user(request):
        if keyword:
            posts = post_keyword_all
        else:
            posts = post_all
    elif is_group_admin(request):
        if keyword:
            posts = post_keyword_all.filter(dept=dept_name)
        else:
            posts = post_all.filter(dept=dept_name)
    elif is_common_user(request):
        if keyword:
            posts = post_keyword_all.filter(applyer=username)
        else:
            posts = post_all.filter(applyer=username)

    return posts


@require_login
def perm_apply_log(request, offset):
    """ 申请记录 """
    header_title, path1, path2 = u'权限申请记录', u'权限管理', u'申请记录'
    keyword = request.GET.get('keyword', '')
    user_id = get_session_user_info(request)[0]
    username = User.objects.get(id=user_id).username
    dept_name = get_session_user_info(request)[4]
    status_dic = {'online': 0, 'offline': 1}
    status = status_dic[offset]
    posts = get_apply_posts(request, status, username, dept_name, keyword)
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
    return render_to_response('jperm/perm_log_%s.html' % offset, locals(), context_instance=RequestContext(request))


@require_login
def perm_apply_info(request):
    """ 申请信息详情 """
    uuid = request.GET.get('uuid', '')
    post = Apply.objects.filter(uuid=uuid)
    username = get_session_user_info(request)[1]
    if post:
        post = post[0]
        if post.read == 0 and post.applyer != username:
            post.read = 1
            post.save()
    else:
        return httperror(request, u'没有这个申请记录!')

    return render_to_response('jperm/perm_apply_info.html', locals(), context_instance=RequestContext(request))


@require_admin
def perm_apply_del(request):
    """ 删除日志记录 """
    uuid = request.GET.get('uuid')
    u_apply = Apply.objects.filter(uuid=uuid)
    if u_apply:
        u_apply.delete()
    return HttpResponseRedirect('/jperm/apply_show/online/')


@require_login
def perm_apply_search(request):
    """ 申请搜索 """
    keyword = request.GET.get('keyword')
    offset = request.GET.get('env')
    username = get_session_user_info(request)[1]
    dept_name = get_session_user_info(request)[3]
    status_dic = {'online': 0, 'offline': 1}
    status = status_dic[offset]
    posts = get_apply_posts(request, status, username, dept_name, keyword)
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
    return render_to_response('jperm/perm_apply_search.html', locals(), context_instance=RequestContext(request))














