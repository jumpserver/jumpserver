# coding:utf-8

from django.db.models import Q
# for django 1.9+
# from django.http import JsonResponse
from japi.http import JsonResponse
from jasset.asset_api import *
from jumpserver.api import *
from jasset.models import Asset, IDC, AssetGroup, ASSET_TYPE, ASSET_STATUS
from jperm.perm_api import get_group_user_perm


#
# jasset api
#

@require_role('admin')
def group_list(request):
    """
    list asset group
    列出资产组

    for django 1.9+
    change model._meta.get_all_field_names()
    to model._meta.get_field()
    """
    keyword = request.GET.get('keyword', '')
    group_id = request.GET.get('id')

    fields = AssetGroup._meta.get_all_field_names()
    asset_group_list = AssetGroup.objects.all()
    if group_id:
        asset_group_list = asset_group_list.filter(id=group_id)
    if keyword:
        asset_group_list = asset_group_list.filter(Q(name__contains=keyword) | Q(comment__contains=keyword))

    return JsonResponse(list(asset_group_list.values(*fields)), safe=False)


#
# jperm api
#

@require_role('admin')
def perm_role_list(request):
    """
    list role page
    """

    # 获取所有系统角色
    fields = PermRole._meta.get_all_field_names()
    roles_list = PermRole.objects.all()
    role_id = request.GET.get('id')
    # TODO: 搜索和分页
    keyword = request.GET.get('search', '')
    if keyword:
        roles_list = roles_list.filter(Q(name=keyword))

    if role_id:
        roles_list = roles_list.filter(id=role_id)

    return JsonResponse(list(roles_list.values(*fields)), safe=False)