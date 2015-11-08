# coding: utf-8
import ast
import xlsxwriter

from jumpserver.api import *
from jasset.models import ASSET_STATUS, ASSET_TYPE, ASSET_ENV, IDC, AssetRecord


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


def db_update_group(**kwargs):
    """
    add a asset group in database
    数据库中更新资产
    """
    group_id = kwargs.pop('id')
    asset_id_list = kwargs.pop('asset_select')
    group = get_object(AssetGroup, id=group_id)

    for asset_id in asset_id_list:
            group_add_asset(group, asset_id)

    AssetGroup.objects.filter(id=group_id).update(**kwargs)


def db_asset_add(**kwargs):
    """
    add asset to db
    添加主机时数据库操作函数
    """
    group_id_list = kwargs.pop('groups')
    asset = Asset(**kwargs)
    asset.save()

    group_select = []
    for group_id in group_id_list:
        group = AssetGroup.objects.filter(id=group_id)
        group_select.extend(group)
    asset.group = group_select


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
# def batch_host_edit(host_alter_dic, j_user='', j_password=''):
#     """ 批量修改主机函数 """
#     j_id, j_ip, j_idc, j_port, j_type, j_group, j_dept, j_active, j_comment = host_alter_dic
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


def sort_ip_list(ip_list):
    """ ip地址排序 """
    ip_list.sort(key=lambda s: map(int, s.split('.')))
    return ip_list


def get_tuple_name(asset_tuple, value):
    """"""
    for t in asset_tuple:
        if t[0] == value:
            return t[1]

    return ''


def get_tuple_diff(asset_tuple, field_name, value):
    """"""
    old_name = get_tuple_name(asset_tuple, int(value[0])) if value[0] else u''
    new_name = get_tuple_name(asset_tuple, int(value[1])) if value[1] else u''
    alert_info = [field_name, old_name, new_name]
    return alert_info


def asset_diff(before, after):
    """
    asset change before and after
    """
    alter_dic = {}
    before_dic, after_dic = before, dict(after.iterlists())
    for k, v in before_dic.items():
        after_dic_values = after_dic.get(k, [])
        if k == 'group':
            after_dic_value = after_dic_values if len(after_dic_values) > 0 else u''
            uv = v if v is not None else u''
        else:
            after_dic_value = after_dic_values[0] if len(after_dic_values) > 0 else u''
            uv = unicode(v) if v is not None else u''
        if uv != after_dic_value:
            alter_dic.update({k: [uv, after_dic_value]})

    for k, v in alter_dic.items():
        if v == [None, u'']:
            alter_dic.pop(k)

    return alter_dic


def db_asset_alert(asset, username, alert_dic):
    """
    asset alert info to db
    """
    alert_list = []
    asset_tuple_dic = {'status': ASSET_STATUS, 'env': ASSET_ENV, 'asset_type': ASSET_TYPE}
    for field, value in alert_dic.iteritems():
        print field
        field_name = Asset._meta.get_field_by_name(field)[0].verbose_name
        if field == 'idc':
            old = IDC.objects.filter(id=value[0])
            new = IDC.objects.filter(id=value[1])
            old_name = old[0].name if old else u''
            new_name = new[0].name if new else u''
            alert_info = [field_name, old_name, new_name]

        elif field in ['status', 'env', 'asset_type']:
            alert_info = get_tuple_diff(asset_tuple_dic.get(field), field_name, value)

        elif field == 'group':
            old, new = [], []
            for group_id in value[0]:
                group_name = AssetGroup.objects.get(id=int(group_id)).name
                old.append(group_name)
            for group_id in value[1]:
                group_name = AssetGroup.objects.get(id=int(group_id)).name
                new.append(group_name)
            alert_info = [field_name, ','.join(old), ','.join(new)]

        elif field == 'use_default_auth':
            pass
        elif field == 'is_active':
            pass

        else:
            alert_info = [field_name, unicode(value[0]), unicode(value[1])]

        if 'alert_info' in dir():
            alert_list.append(alert_info)

    if alert_list:
        AssetRecord.objects.create(asset=asset, username=username, content=alert_list)


def write_excel(asset_all):
    data = []
    now = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M')
    file_name = 'cmdb_excel_' + now + '.xlsx'
    workbook = xlsxwriter.Workbook('static/files/excels/%s' % file_name)
    worksheet = workbook.add_worksheet(u'CMDB数据')
    worksheet.set_first_sheet()
    worksheet.set_column('A:Z', 14)
    title = [u'主机名', u'IP', u'IDC', u'MAC', u'远控IP', u'CPU', u'内存', u'硬盘', u'操作系统', u'机柜位置',
             u'所属主机组', u'机器状态', u'备注']
    for asset in asset_all:
        group_list = []
        for p in asset.group.all():
            group_list.append(p.name)

        group_all = '/'.join(group_list)
        status = asset.get_status_display()
        alter_dic = [asset.hostname, asset.ip, asset.idc.name, asset.mac, asset.remote_ip, asset.cpu, asset.memory,
                asset.disk, asset.system_type, asset.cabinet, group_all, status, asset.comment]
        data.append(alter_dic)
    format = workbook.add_format()
    format.set_border(1)
    format.set_align('center')

    format_title = workbook.add_format()
    format_title.set_border(1)
    format_title.set_bg_color('#cccccc')
    format_title.set_align('center')
    format_title.set_bold()

    format_ave = workbook.add_format()
    format_ave.set_border(1)
    format_ave.set_num_format('0.00')

    worksheet.write_row('A1', title, format_title)
    i = 2
    for alter_dic in data:
        location = 'A' + str(i)
        worksheet.write_row(location, alter_dic, format)
        i += 1

    workbook.close()
    ret = (True, file_name)
    return ret
