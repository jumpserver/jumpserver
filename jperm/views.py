# coding: utf-8

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from juser.models import User, UserGroup
from jasset.models import Asset, BisGroup
from jperm.models import Perm
from django.core.paginator import Paginator, EmptyPage, InvalidPage


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


