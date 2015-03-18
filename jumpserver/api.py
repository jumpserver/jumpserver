#coding: utf-8

from django.http import HttpResponseRedirect
import json

from django.http import HttpResponse

from juser.models import User, UserGroup
from jasset.models import Asset, BisGroup
from jlog.models import Log


def user_perm_group_api(username):
    user = User.objects.get(username=username)
    if user:
        perm_list = []
        user_group_all = user.group.all()
        for user_group in user_group_all:
            perm_list.extend(user_group.perm_set.all())

        asset_group_list = []
        for perm in perm_list:
            asset_group_list.append(perm.asset_group)
        return asset_group_list


def user_perm_asset_api(username):
    user = User.objects.filter(username=username)
    if user:
        user = user[0]
        asset_list = []
        asset_group_list = user_perm_group_api(user)
        for asset_group in asset_group_list:
            asset_list.extend(asset_group.asset_set.all())

        return asset_list


def asset_perm_api(asset):
    if asset:
        perm_list = []
        asset_group_all = asset.bis_group.all()
        for asset_group in asset_group_all:
            perm_list.extend(asset_group.perm_set.all())

        user_group_list = []
        for perm in perm_list:
            user_group_list.extend(perm.user_group.all())

        user_permed_list = []
        for user_group in user_group_list:
            user_permed_list.extend(user_group.user_set.all())
        return user_permed_list


def require_login(func):
    """要求登录的装饰器"""
    def _deco(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return HttpResponseRedirect('/login/')
        return func(request, *args, **kwargs)
    return _deco


def require_super_user(func):
    def _deco(request, *args, **kwargs):
        if request.session.get('role_id', 0) != 2:
            print "##########%s" % request.session.get('role_id', 0)
            return HttpResponseRedirect('/')
        return func(request, *args, **kwargs)
    return _deco


def require_admin(func):
    def _deco(request, *args, **kwargs):
        if request.session.get('role_id', 0) < 1:
            return HttpResponseRedirect('/')
        return func(request, *args, **kwargs)
    return _deco


def is_super_user(request):
    if request.session.get('role_id') == 2:
        return True
    else:
        return False


def is_group_admin(request):
    print request.session.get('role_id'), type(request.session.get('role_id'))
    if request.session.get('role_id') == 1:
        return True
    else:
        return False


def get_user_dept(request):
    user_id = request.session.get('user_id')
    if user_id:
        user_dept = User.objects.get(id=user_id).dept
        return user_dept.id


def api_user(request):
    hosts = Log.objects.filter(is_finished=0).count()
    users = Log.objects.filter(is_finished=0).values('user').distinct().count()
    ret = {'users': users, 'hosts': hosts}
    json_data = json.dumps(ret)
    return HttpResponse(json_data)
