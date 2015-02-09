# coding: utf-8

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from juser.models import User, UserGroup
from jasset.models import Asset, BisGroup
from jperm.models import Perm, SudoPerm, CmdGroup
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.db.models import Q


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


def perm_user_asset(user_id=None, username=None):
    if user_id:
        user = User.objects.get(id=user_id)
    else:
        user = User.objects.get(username=username)
    user_groups = user.user_group.all()
    perms = []
    assets = []
    for user_group in user_groups:
        perm = user_group.perm_set.all()
        perms.extend(perm)

    asset_groups = [perm.asset_group for perm in perms]

    for asset_group in asset_groups:
        assets.extend(list(asset_group.asset_set.all()))

    return list(set(assets))


def perm_list(request):
    header_title, path1, path2 = u'主机授权 | Perm Host Detail.', u'jperm', u'perm_list'
    groups = contact_list = UserGroup.objects.all().order_by('type')
    users = contact_list2 = User.objects.all().order_by('id')
    p = paginator = Paginator(contact_list, 10)
    p2 = paginator2 = Paginator(contact_list2, 10)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        contacts = paginator.page(page)
        contacts2 = paginator2.page(page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)
        contacts2 = paginator2.page(paginator2.num_pages)
    return render_to_response('jperm/perm_list.html', locals())


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
        header_title, path1, path2 = u'编辑授权 | Perm Host Edit.', u'jperm', u'perm_edit'
        user_group_id = request.GET.get('id')
        user_group = UserGroup.objects.get(id=user_group_id)
        asset_groups = BisGroup.objects.all()
        asset_groups_permed = [perm.asset_group for perm in user_group.perm_set.all()]
        asset_groups_unperm = [asset_group for asset_group in asset_groups if asset_group not in asset_groups_permed]
        return render_to_response('jperm/perm_edit.html', locals())
    else:
        user_group_name = request.POST.get('user_group_name')
        asset_groups_selected = request.POST.getlist('asset_group_permed')
        perm_group_update(user_group_name=user_group_name, asset_groups_id=asset_groups_selected)
        return HttpResponseRedirect('/jperm/perm_list/')


def perm_detail(request):
    user_group_id = request.GET.get('id')
    user_group = UserGroup.objects.get(id=user_group_id)
    asset_groups = [perm.asset_group for perm in user_group.perm_set.all()]
    return render_to_response('jperm/perm_detail.html', locals())


def perm_del(request):
    user_group_id = request.GET.get('id')
    user_group = UserGroup.objects.get(id=user_group_id)
    Perm.objects.filter(user_group=user_group).delete()
    return HttpResponseRedirect('/jperm/perm_list/')


def perm_asset_detail(request):
    user_id = request.GET.get('id')
    user = User.objects.get(id=user_id)
    assets = perm_user_asset(user_id)
    return render_to_response('jperm/perm_asset_detail.html', locals())



def user_asset_cmd_groups_get(user_groups_select, asset_groups_select, cmd_groups_select):
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


def sudo_db_add(user_groups_select, asset_groups_select, cmd_groups_select, comment):
    user_groups_select_list, asset_groups_select_list, cmd_groups_select_list = \
        user_asset_cmd_groups_get(user_groups_select, asset_groups_select, cmd_groups_select)

    sudo_perm = SudoPerm(comment=comment)
    sudo_perm.save()
    sudo_perm.user_group = user_groups_select_list
    sudo_perm.asset_group = asset_groups_select_list
    sudo_perm.cmd_group = cmd_groups_select_list


def sudo_ldap_add(user_groups_select, asset_groups_select, cmd_groups_select):
    user_groups_select_list, asset_groups_select_list, cmd_groups_select_list = \
        user_asset_cmd_groups_get(user_groups_select, asset_groups_select, cmd_groups_select)


def sudo_add(request):
    header_title, path1, path2 = u'Sudo授权 | Perm Sudo Add.', u'jperm', u'sudo_add'
    user_groups = UserGroup.objects.filter(Q(type='A') | Q(type='P')).order_by('type')
    asset_groups = BisGroup.objects.all().order_by('type')
    cmd_groups = CmdGroup.objects.all()

    if request.method == 'POST':
        user_groups_select = request.POST.getlist('user_groups_select')
        asset_groups_select = request.POST.getlist('asset_groups_select')
        cmd_groups_select = request.POST.getlist('cmd_groups_select')
        comment = request.POST.get('comment', '')

        sudo_db_add(user_groups_select, asset_groups_select, cmd_groups_select, comment)


        msg = '添加成功'

    return render_to_response('jperm/sudo_add.html', locals())


def sudo_list(request):
    header_title, path1, path2 = u'Sudo授权 | Perm Sudo Detail.', u'jperm', u'sudo_list'
    sudo_perms = contact_list2 = SudoPerm.objects.all()
    p2 = paginator2 = Paginator(contact_list2, 10)
    user_groups = UserGroup.objects.filter(Q(type='A') | Q(type='P'))
    asset_groups = BisGroup.objects.all()
    cmd_groups = CmdGroup.objects.all()
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        contacts2 = paginator2.page(page)
    except (EmptyPage, InvalidPage):
        contacts2 = paginator2.page(paginator2.num_pages)
    return render_to_response('jperm/sudo_list.html', locals())


def cmd_add(request):
    header_title, path1, path2 = u'sudo命令添加 | Sudo Cmd Add.', u'jperm', u'sudo_cmd_add'

    if request.method == 'POST':
        name = request.POST.get('name')
        cmd = ','.join(request.POST.get('cmd').split())
        comment = request.POST.get('comment')

        CmdGroup.objects.create(name=name, cmd=cmd, comment=comment)
        msg = u'命令组添加成功'

    return render_to_response('jperm/sudo_cmd_add.html', locals())


def cmd_list(request):
    header_title, path1, path2 = u'sudo命令查看 | Sudo Cmd List.', u'jperm', u'sudo_cmd_list'

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
    return render_to_response('jperm/sudo_cmd_list.html', locals())

