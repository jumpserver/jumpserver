# -*- coding: utf-8 -*-
#
from common.utils import get_logger
from .base import BasePam

__all__ = ['PamAPi', 'PamDevAPi', 'PamAccountAPi']

logger = get_logger(__name__)


class PamDevAPi:
    client: None

    # 资产类型
    def dev_type(self, name, sys_type_group=None, method='get'):
        path = '/api/devType'
        if method == 'get':
            return self.client.adapter.get(path)
        data = {'name': name, 'sysTypeGroup': {'name': sys_type_group}}
        return self.client.adapter.post(path, json=data)

    def delete_dev_type(self, pk):
        path = '/api/devType/{}'.format(pk)
        return self.client.adapter.delete(path)

    def create_dev(self, name, ip, sys_type, department, database_data=None):
        if database_data is None:
            database_data = {}

        path = '/api/dev'
        data = {
            'name': name,
            'ip': ip,
            'sysType': sys_type,
            'department': department,
            'networkEnvironment': {'id': 1},
            "charset": "UTF-8"
        }
        if database_data:
            data.update(database_data)
        return self.client.adapter.post(path, json=data)

    def filter_dev(self, name, sys_type, department, ip=1):
        path = '/api/dev'
        data = {
            'nameContains': name,
            'ipContains': ip,
            'sysType.nameIs': sys_type,
            'department.idIs': department,
            'deletedIs': False
        }
        return self.client.adapter.get(path, params=data)['content']

    def delete_dev(self, pk):
        path = '/api/dev/{}'.format(pk)
        return self.client.adapter.delete(path)


class PamAccountAPi:
    client: None

    def filter_account(self, name, department, asset_name, ip=1):
        path = '/api/dev'
        data = {
            'accountNameCustom': name,
            'ipContains': ip,
            'department.idIs': department,
            'nameContains': asset_name
        }
        return self.client.adapter.get(path, params=data)['content']

    def create_or_update_account(self, name, password, asset_id):
        path = '/api/dev/changeAccount/{}'.format(asset_id)
        data = {
            'name': name,
            'password': password
        }
        return self.client.adapter.put(path, params=data)

    def department(self, name, method='get'):
        path = '/api/department'
        if method == 'get':
            return self.client.adapter.get(path)
        data = {'name': name, 'parent': {'id': 1}}
        return self.client.adapter.post(path, json=data)

    def get_pwd(self, name, ip, account):
        path = '/api/perm/devAccPwd'
        data = {'name': name, 'ip': ip, 'account': account}
        return self.client.adapter.post(path, json=data)


class PamAPi(PamDevAPi, PamAccountAPi, BasePam):

    def __init__(self, url, username=None, password=None):
        super().__init__(url, username, password)

    def init_assets_apps(self):
        pass
