# coding: utf-8
from __future__ import division
import xlrd
import xlsxwriter
from django.db.models import AutoField
from jumpserver.api import *
from jasset.models import ASSET_STATUS, ASSET_TYPE, ASSET_ENV, IDC, AssetRecord
from jperm.ansible_api import MyRunner
from jperm.perm_api import gen_resource
from jumpserver.templatetags.mytags import get_disk_info

import traceback


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


def db_asset_update(**kwargs):
    """ 修改主机时数据库操作函数 """
    asset_id = kwargs.pop('id')
    Asset.objects.filter(id=asset_id).update(**kwargs)


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


def asset_diff_one(before, after):
    print before.__dict__, after.__dict__
    fields = Asset._meta.get_all_field_names()
    for field in fields:
        print before.field, after.field


def db_asset_alert(asset, username, alert_dic):
    """
    asset alert info to db
    """
    alert_list = []
    asset_tuple_dic = {'status': ASSET_STATUS, 'env': ASSET_ENV, 'asset_type': ASSET_TYPE}
    for field, value in alert_dic.iteritems():
        field_name = Asset._meta.get_field_by_name(field)[0].verbose_name
        if field == 'idc':
            old = IDC.objects.filter(id=value[0]) if value[0] else u''
            new = IDC.objects.filter(id=value[1]) if value[1] else u''
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
            if sorted(old) == sorted(new):
                continue
            else:
                alert_info = [field_name, ','.join(old), ','.join(new)]

        elif field == 'use_default_auth':
            if unicode(value[0]) == 'True' and unicode(value[1]) == 'on' or \
                                    unicode(value[0]) == 'False' and unicode(value[1]) == '':
                continue
            else:
                name = asset.username
                alert_info = [field_name, u'默认', name] if unicode(value[0]) == 'True' else \
                    [field_name, name, u'默认']

        elif field in ['username', 'password']:
            continue

        elif field == 'is_active':
            if unicode(value[0]) == 'True' and unicode(value[1]) == '1' or \
                                    unicode(value[0]) == 'False' and unicode(value[1]) == '0':
                continue
            else:
                alert_info = [u'是否激活', u'激活', u'禁用'] if unicode(value[0]) == 'True' else \
                    [u'是否激活', u'禁用', u'激活']

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
    worksheet.set_column('A:E', 15)
    worksheet.set_column('F:F', 40)
    worksheet.set_column('G:Z', 15)
    title = [u'主机名', u'IP', u'IDC', u'所属主机组', u'操作系统', u'CPU', u'内存(G)', u'硬盘(G)',
             u'机柜位置', u'MAC', u'远控IP', u'机器状态', u'备注']
    for asset in asset_all:
        group_list = []
        for p in asset.group.all():
            group_list.append(p.name)

        disk = get_disk_info(asset.disk)
        group_all = '/'.join(group_list)
        status = asset.get_status_display()
        idc_name = asset.idc.name if asset.idc else u''
        system_type = asset.system_type if asset.system_type else u''
        system_version = asset.system_version if asset.system_version else u''
        system_os = unicode(system_type) + unicode(system_version)

        alter_dic = [asset.hostname, asset.ip, idc_name, group_all, system_os, asset.cpu, asset.memory,
                     disk, asset.cabinet, asset.mac, asset.remote_ip, status, asset.comment]
        data.append(alter_dic)
    format = workbook.add_format()
    format.set_border(1)
    format.set_align('center')
    format.set_align('vcenter')
    format.set_text_wrap()

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


def copy_model_instance(obj):
    initial = dict([(f.name, getattr(obj, f.name))
                    for f in obj._meta.fields
                    if not isinstance(f, AutoField) and \
                    not f in obj._meta.parents.values()])
    return obj.__class__(**initial)


def ansible_record(asset, ansible_dic, username):
    alert_dic = {}
    asset_dic = asset.__dict__
    for field, value in ansible_dic.items():
        old = asset_dic.get(field)
        new = ansible_dic.get(field)
        if unicode(old) != unicode(new):
            setattr(asset, field, value)
            asset.save()
            alert_dic[field] = [old, new]

    db_asset_alert(asset, username, alert_dic)


def excel_to_db(excel_file):
    """
    Asset add batch function
    """
    try:
        data = xlrd.open_workbook(filename=None, file_contents=excel_file.read())
    except Exception, e:
        return False
    else:
        table = data.sheets()[0]
        rows = table.nrows
        for row_num in range(1, rows):
            row = table.row_values(row_num)
            if row:
                group_instance = []
                ip, port, hostname, use_default_auth, username, password, group = row
                if get_object(Asset, hostname=hostname):
                    continue
                if isinstance(password, int) or isinstance(password, float):
                    password = unicode(int(password))
                use_default_auth = 1 if use_default_auth == u'默认' else 0
                password_encode = CRYPTOR.encrypt(password) if password else ''
                if hostname:
                    asset = Asset(ip=ip,
                                  port=port,
                                  hostname=hostname,
                                  use_default_auth=use_default_auth,
                                  username=username,
                                  password=password_encode
                                  )
                    asset.save()
                    group_list = group.split('/')
                    for group_name in group_list:
                        group = get_object(AssetGroup, name=group_name)
                        if group:
                            group_instance.append(group)
                    if group_instance:
                        asset.group = group_instance
                    asset.save()
        return True


def get_ansible_asset_info(asset_ip, setup_info):
    disk_need = {}
    disk_all = setup_info.get("ansible_devices")
    if disk_all:
        for disk_name, disk_info in disk_all.iteritems():
            if disk_name.startswith('sd') or disk_name.startswith('hd') or disk_name.startswith('vd') or disk_name.startswith('xvd'):
                disk_size = disk_info.get("size", '')
                if 'M' in disk_size:
                    disk_format = round(float(disk_size[:-2]) / 1000, 0)
                elif 'T' in disk_size:
                    disk_format = round(float(disk_size[:-2]) * 1000, 0)
                else:
                    disk_format = float(disk_size[:-2])
                disk_need[disk_name] = disk_format
    all_ip = setup_info.get("ansible_all_ipv4_addresses")
    other_ip_list = all_ip.remove(asset_ip) if asset_ip in all_ip else []
    other_ip = ','.join(other_ip_list) if other_ip_list else ''
    # hostname = setup_info.get("ansible_hostname")
    # ip = setup_info.get("ansible_default_ipv4").get("address")
    mac = setup_info.get("ansible_default_ipv4").get("macaddress")
    brand = setup_info.get("ansible_product_name")
    try:
        cpu_type = setup_info.get("ansible_processor")[1]
    except IndexError:
        cpu_type = ' '.join(setup_info.get("ansible_processor")[0].split(' ')[:6])

    memory = setup_info.get("ansible_memtotal_mb")
    try:
        memory_format = int(round((int(memory) / 1000), 0))
    except Exception:
        memory_format = memory
    disk = disk_need
    system_type = setup_info.get("ansible_distribution")
    if system_type.lower() == "freebsd":
        system_version = setup_info.get("ansible_distribution_release")
        cpu_cores = setup_info.get("ansible_processor_count")
    else:
        system_version = setup_info.get("ansible_distribution_version")
        cpu_cores = setup_info.get("ansible_processor_vcpus")
    cpu = cpu_type + ' * ' + unicode(cpu_cores)
    system_arch = setup_info.get("ansible_architecture")
    # asset_type = setup_info.get("ansible_system")
    sn = setup_info.get("ansible_product_serial")
    asset_info = [other_ip, mac, cpu, memory_format, disk, sn, system_type, system_version, brand, system_arch]
    return asset_info


def asset_ansible_update(obj_list, name=''):
    resource = gen_resource(obj_list)
    ansible_instance = MyRunner(resource)
    ansible_asset_info = ansible_instance.run(module_name='setup', pattern='*')
    logger.debug('获取硬件信息: %s' % ansible_asset_info)
    for asset in obj_list:
        try:
            setup_info = ansible_asset_info['contacted'][asset.hostname]['ansible_facts']
            logger.debug("setup_info: %s" % setup_info)
        except KeyError, e:
            logger.error("获取setup_info失败: %s" % e)
            continue
        else:
            try:
                asset_info = get_ansible_asset_info(asset.ip, setup_info)
                print asset_info
                other_ip, mac, cpu, memory, disk, sn, system_type, system_version, brand, system_arch = asset_info
                asset_dic = {"other_ip": other_ip,
                             "mac": mac,
                             "cpu": cpu,
                             "memory": memory,
                             "disk": disk,
                             "sn": sn,
                             "system_type": system_type,
                             "system_version": system_version,
                             "system_arch": system_arch,
                             "brand": brand
                             }

                ansible_record(asset, asset_dic, name)
            except Exception as e:
                logger.error("save setup info failed! %s" % e)
                traceback.print_exc()


def asset_ansible_update_all():
    name = u'定时更新'
    asset_all = Asset.objects.all()
    asset_ansible_update(asset_all, name)

