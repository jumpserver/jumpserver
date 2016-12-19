# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from ops.tasks import _celery_tasks

from ops.models import TaskRecord
from uuid import uuid1
from celery.result import AsyncResult

__all__ = ["get_result",
           "start_get_hardware_info",
           "start_ping_test",
           "get_hardware_info",
           "get_ping_test"]


def get_result(task_id):
    result = AsyncResult(task_id)
    if result.ready():
        return {"Completed": True, "data": result.get()}
    else:
        return {"Completed": False, "data": None}


def __get_result_by_tasker_id(tasker_uuid, deal_method):
    tasker = TaskRecord.objects.get(uuid=tasker_uuid)
    total = tasker.total_hosts
    total_len = len(total)
    host_results = []

    # 存储数据
    for play in tasker.plays.all():
        for t in play.tasks.all():
            task = {'name': t.name, 'uuid': t.uuid, 'percentage': 0, 'completed': {'success': {}, 'failed': {}}}
            completed = []
            count = 0
            for h in t.host_results.all():
                completed.append(h.name)
                count += 1
                if h.is_success:
                    result = getattr(h, deal_method)
                    if result.get('msg') is None:
                        task['completed']['success'][h.name] = result.get('data')
                    else:
                        task['completed']['failed'][h.name] = result.get('msg')
                else:
                    task['completed']['failed'][h.name] = h.failed_msg

            # 计算进度
            task['percentage'] = float(count * 100 / total_len)
            task['waited'] = list(set(total) - set(completed))

            host_results.append(task)

    return host_results


def start_get_hardware_info(*assets):
    name = "Get host hardware information"
    uuid = "tasker-" + uuid1().hex
    _celery_tasks.get_asset_hardware_info.delay(name, uuid, *assets)
    return uuid


def __get_hardware_info(tasker_uuid):
    return __get_result_by_tasker_id(tasker_uuid, 'deal_setup')


def get_hardware_info(tasker_uuid):
    """

    :param assets: 资产列表
    :return: 返回数据结构样列
        {u'data': [{u'completed': {
                        u'failed': {u'192.168.232.135': u'Authentication failure.'},
                        u'success': {u'192.168.1.119': {u'cpu': u'GenuineIntel Intel Xeon E312xx (Sandy Bridge) 6\u6838',
                                                        u'disk': {<device_name>: <device_detail_dict>},
                                                        u'env': {<env_name>: <env_value>},
                                                        u'interface': {<interface_name>: <interface_detail_dict>},
                                                        u'mem': 3951,
                                                        u'os': u'Ubuntu 16.04(xenial)',
                                                        u'sn': u'NA'}}},
                   u'name': u'',
                   u'percentage': 100.0,
                   u'uuid': u'87cfedfe-ba55-44ff-bc43-e7e73b869ca1',
                   u'waited': []}
                  ],
         u'msg': None}
    """
    try:
        return {"msg": None, "data": __get_hardware_info(tasker_uuid)}
    except Exception as e:
        return {"msg": "query data failed!, %s" % e.message, "data": None}


def start_ping_test(*assets):
    name = "Test host connection"
    uuid = "tasker-" + uuid1().hex
    _celery_tasks.asset_test_ping_check.delay(name, uuid, *assets)
    return uuid


def __get_ping_test(tasker_uuid):
    return __get_result_by_tasker_id(tasker_uuid, 'deal_ping')


def get_ping_test(tasker_uuid):
    """

    :param assets: 资产列表
    :return: 返回数据结构样列
        {u'data': [{u'completed': {
                        u'failed': {u'192.168.232.135': u'Authentication failure.'},
                        u'success': {u'192.168.1.119': {u'success': True}}},
                    u'name': u'',
                    u'percentage': 100.0,
                    u'uuid': u'3e6e0d3b-bee0-4383-b19e-bec6ba55d346',
                    u'waited': []}
                  ],
         u'msg': None}
    """
    try:
        return {"msg": None, "data": __get_ping_test(tasker_uuid)}
    except Exception as e:
        return {"msg": "query data failed!, %s" % e.message, "data": None}

