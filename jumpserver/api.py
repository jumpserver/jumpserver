__author__ = 'guanghongwei'

import json

from django.http import HttpResponse

from juser.models import User, UserGroup
from jasset.models import Asset, BisGroup
from jlog.models import Log


def user_perm_group_api(user):
    if user:
        perm_list = []
        user_group_all = user.group.all()
        for user_group in user_group_all:
            perm_list.extend(user_group.perm_set.all())

        asset_group_list = []
        for perm in perm_list:
            asset_group_list.extend(perm.asset_group.all())

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


def api_user(request):
    hosts = Log.objects.filter(is_finished=0).count()
    users = Log.objects.filter(is_finished=0).values('user').distinct().count()
    ret = {'users': users, 'hosts': hosts}
    json_data = json.dumps(ret)
    return HttpResponse(json_data)
