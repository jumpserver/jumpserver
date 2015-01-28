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


# def perm_user_host(username, ips):
#     user = User.objects.get(username=username)
#     user.perm_set.all().delete()
#     for ip in ips:
#         asset = Asset.objects.get(ip=ip)
#         Perm.objects.create(user=user, asset=asset)
#
#
# def perm_user_edit(request):
#     header_title, path1, path2 = u'授权编辑 | Perm Edit.', u'jperm', u'perm_edit'
#     if request.method == 'GET':
#         if request.GET.get('id', None):
#             user_id = request.GET.get('id')
#             user = User.objects.get(id=user_id)
#             assets = Asset.objects.all()
#             assets_permed = []
#             for perm in user.perm_set.all():
#                 assets_permed.append(perm.asset)
#             assets_unperm = list(set(assets)-set(assets_permed))
#             return render_to_response('jperm/perm_user_edit.html', locals())
#     else:
#         host_ips = request.POST.getlist('host_permed', '')
#         username = request.POST.get('username')
#         perm_user_host(username, host_ips)
#
#         return HttpResponseRedirect('/jperm/perm_host/')
#
#
# def perm_user_detail(request):
#     user_id = request.GET.get('id', '')
#     user = User.objects.get(id=user_id)
#     host_permed = []
#     for perm in user.perm_set.all():
#         host_permed.append(perm.asset)
#
#     return render_to_response('jperm/perm_user_detail.html', locals())
#
#
# def perm_group_edit(request):
#     if request.method == 'GET':
#         group_id = request.GET.get('id', '')
#         group = UserGroup.objects.get(id=group_id)
#
#         return render_to_response('jperm/perm_group_edit.html')
#
#
# def perm_add(request):
#     header_title, path1, path2 = u'添加授权 | Add User perm.', u'授权管理', u'添加授权'
#     if request.method == 'GET':
#         username = request.GET.get('username', None)
#         if not username:
#             return HttpResponseRedirect('/')
#
#         user = User.objects.get(username=username)
#         permed_hosts = []
#         for perm in user.perm_set.all():
#             permed_hosts.append(perm.asset)
#
#         hosts_all = Asset.objects.all()
#         hosts = list(set(hosts_all) - set(permed_hosts))
#
#     else:
#         username = request.POST.get('username', None)
#         host_ids = request.POST.getlist('host_ids', None)
#
#         user = User.objects.get(username=username)
#         for host_id in host_ids:
#             asset = Asset.objects.get(id=host_id)
#             perm = Perm(user=user, asset=asset)
#             perm.save()
#             msg = u'添加成功'
#
#     return render_to_response('jperm/perm_add.html', locals())
#
#
# def perm_user_show(request):
#     header_title, path1, path2 = u'查看授权用户 | Perm User Detail.', u'授权管理', u'用户详情'
#     users = User.objects.all()
#     return render_to_response('jperm/perm_user_show.html', locals(),)


