# coding: utf-8
from jumpserver.api import *


def group_add_asset(group, asset_id=None, asset_ip=None):
    """
    资产组添加资产
    Asset group add a asset
    """
    if asset_id:
        asset = get_object(Asset, id=asset_id)
    else:
        asset = get_object(Asset, ip=asset_ip)

    if asset:
        group.asset_set.add(asset)


def db_add_group(**kwargs):
    """
    add a asset group in database
    数据库中添加资产
    """
    name = kwargs.get('name')
    group = get_object(AssetGroup, name=name)
    asset_id_list = kwargs.pop('asset_select')

    if not group:
        group = AssetGroup(**kwargs)
        group.save()
        for asset_id in asset_id_list:
            group_add_asset(group, asset_id)


def db_asset_add(**kwargs):
    """
    add asset to db
    添加主机时数据库操作函数
    """

    Asset(**kwargs).save()


#
# def get_host_groups(groups):
#     """ 获取主机所属的组类 """
#     ret = []
#     for group_id in groups:
#         group = BisGroup.objects.filter(id=group_id)
#         if group:
#             group = group[0]
#             ret.append(group)
#     group_all = get_object_or_404(BisGroup, name='ALL')
#     ret.append(group_all)
#     return ret
#
#
# # def get_host_depts(depts):
# #     """ 获取主机所属的部门类 """
# #     ret = []
# #     for dept_id in depts:
# #         dept = DEPT.objects.filter(id=dept_id)
# #         if dept:
# #             dept = dept[0]
# #             ret.append(dept)
# #     return ret
#
#


def db_asset_update(**kwargs):
    """ 修改主机时数据库操作函数 """
    asset_id = kwargs.pop('id')
    Asset.objects.filter(id=asset_id).update(**kwargs)

#
#
# def batch_host_edit(host_info, j_user='', j_password=''):
#     """ 批量修改主机函数 """
#     j_id, j_ip, j_idc, j_port, j_type, j_group, j_dept, j_active, j_comment = host_info
#     groups, depts = [], []
#     is_active = {u'是': '1', u'否': '2'}
#     login_types = {'LDAP': 'L', 'MAP': 'M'}
#     a = Asset.objects.get(id=j_id)
#     if '...' in j_group[0].split():
#         groups = a.bis_group.all()
#     else:
#         for group in j_group[0].split():
#             c = BisGroup.objects.get(name=group.strip())
#             groups.append(c)
#
#     if '...' in j_dept[0].split():
#         depts = a.dept.all()
#     else:
#         for d in j_dept[0].split():
#             p = DEPT.objects.get(name=d.strip())
#             depts.append(p)
#
#     j_type = login_types[j_type]
#     j_idc = IDC.objects.get(name=j_idc)
#     if j_type == 'M':
#         if a.password != j_password:
#             j_password = cryptor.decrypt(j_password)
#         a.ip = j_ip
#         a.port = j_port
#         a.login_type = j_type
#         a.idc = j_idc
#         a.is_active = j_active
#         a.comment = j_comment
#         a.username = j_user
#         a.password = j_password
#     else:
#         a.ip = j_ip
#         a.port = j_port
#         a.idc = j_idc
#         a.login_type = j_type
#         a.is_active = is_active[j_active]
#         a.comment = j_comment
#     a.save()
#     a.bis_group = groups
#     a.dept = depts
#     a.save()
#
#
# def db_host_delete(request, host_id):
#     """ 删除主机操作 """
#     if is_group_admin(request) and not validate(request, asset=[host_id]):
#         return httperror(request, '删除失败, 您无权删除!')
#
#     asset = Asset.objects.filter(id=host_id)
#     if asset:
#         asset.delete()
#     else:
#         return httperror(request, '删除失败, 没有此主机!')
#
#
# def db_idc_delete(request, idc_id):
#     """ 删除IDC操作 """
#     if idc_id == 1:
#         return httperror(request, '删除失败, 默认IDC不能删除!')
#
#     default_idc = IDC.objects.get(id=1)
#
#     idc = IDC.objects.filter(id=idc_id)
#     if idc:
#         idc_class = idc[0]
#         idc_class.asset_set.update(idc=default_idc)
#         idc.delete()
#     else:
#         return httperror(request, '删除失败, 没有这个IDC!')

