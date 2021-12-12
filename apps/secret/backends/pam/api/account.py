# -*- coding: utf-8 -*-
#
__all__ = ['AccountAPi', ]


class AccountAPi:
    client: None

    def read_account_uuid(self):
        path = '/api/account/find/uuid'
        return self.client.adapter.get(path)

    def read_account(self, name, department, asset_name, ip):
        path = '/api/dev'
        data = {
            'accountNameCustom': name,
            'ipContains': ip,
            'department.idIs': department,
            'nameContains': asset_name
        }
        return self.client.adapter.get(path, params=data)['content']

    def delete_account(self, dev_name, account_name):
        uid = self.read_account_uuid()
        path = '/api/account/batch/delete/-1/{}'.format(uid)
        data = [{
            "devName": dev_name,
            "name": account_name
        }]
        return self.client.adapter.put(path, json=data)

    def read_department(self):
        path = '/api/department'
        return self.client.adapter.get(path)

    def read_department_id(self, name):
        departments = self.read_department()
        try:
            department = next(filter(lambda x: name == x['name'], departments))
        except StopIteration:
            department = self.creat_department(name=name)
        return department['id']

    def creat_department(self, name):
        path = '/api/department'
        data = {'name': name, 'parent': {'id': 1}}
        return self.client.adapter.post(path, json=data)

    def create_or_update_account(self, account_name, dev_id, password):
        path = '/api/dev/changeAccount/{}'.format(dev_id)
        data = {
            'name': account_name,
            'password': password
        }
        return self.client.adapter.put(path, json=data)

    def get_pwd(self, dev_name, account_name, ip):
        path = '/api/perm/devAccPwd'
        data = {'name': dev_name, 'ip': ip, 'account': account_name}
        return self.client.adapter.post(path, json=data)
