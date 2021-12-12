# -*- coding: utf-8 -*-
#
__all__ = ['DevAPi', ]


class DevAPi:
    client: None
    DEV_TYPE_MAP = {
        'ssh': {
            'name': 'SSH',
            'sysTypeGroup': 'Linux',
            'type': 0,
            'services': {}
        },
        'telnet': {
            'name': 'Telnet',
            'sysTypeGroup': 'Linux',
            'type': 0,
            'services': {}
        },
        'rdp': {
            'name': 'RDP',
            'sysTypeGroup': 'Windows',
            'type': 0,
            'services': {}
        },
        'vnc': {
            'name': 'VNC',
            'sysTypeGroup': 'Windows',
            'type': 0,
            'services': {}
        },
        'mysql': {
            'name': 'MYSQL',
            'sysTypeGroup': 'Database',
            'type': 2,
            'services': {
                'services': {
                    'services': {
                        'MYSQL': {
                            "database": "MYSQL",
                            "port": 3306
                        }
                    }
                }
            }
        },
        'oracle': {
            'name': 'Oracle',
            'sysTypeGroup': 'Database',
            'type': 2,
            'services': {
                'services': {
                    'services': {
                        'Oracle': {
                            "connectType": "service_name",
                            "service_name": "oracle",
                            "port": 1521
                        }
                    }
                }
            }
        },
        'mariadb': {
            'name': 'MariaDB',
            'sysTypeGroup': 'Database',
            'type': 2,
            'services': {
                'services': {
                    'services': {
                        'MariaDB': {
                            "database": "MariaDB",
                            "port": 3306
                        }
                    }
                }
            }
        },
        'postgresql': {
            'name': 'PgSQL',
            'sysTypeGroup': 'Database',
            'type': 2,
            'services': {
                'services': {
                    'services': {
                        'PgSQL': {
                            "database": "PgSQL",
                            "port": 5432
                        }
                    }
                }
            }
        },
        'sqlserver': {
            'name': 'MSSQL',
            'sysTypeGroup': 'Database',
            'type': 2,
            'services': {
                'services': {
                    'services': {
                        'MSSQL': {
                            "database": "MSSQL",
                            "port": 1433
                        }
                    }
                }
            }
        }
    }

    # 资产类型
    def read_dev_type(self):
        path = '/api/devType'
        return self.client.adapter.get(path)

    def read_dev_type_id(self, type_name):
        sys_type_group = self.DEV_TYPE_MAP[type_name]['sysTypeGroup']
        type_name = self.DEV_TYPE_MAP[type_name]['name']
        dev_types = self.read_dev_type()
        try:
            dev_type = next(filter(lambda x: x['name'].lower() == type_name.lower(), dev_types))
        except StopIteration:
            dev_type = self.create_dev_type(name=type_name, sys_type_group=sys_type_group)
        return dev_type['id']

    def read_dev_id(self, name, type_name, department_id, ip='1'):
        type_name = self.DEV_TYPE_MAP[type_name]['name']
        content = self.read_dev(name, type_name, department_id, ip)
        return content[0]['id'] if content else None

    def create_dev_type(self, name='', sys_type_group=None):
        path = '/api/devType'
        data = {'name': name, 'sysTypeGroup': {'name': sys_type_group}}
        return self.client.adapter.post(path, json=data)

    def delete_dev_type(self, pk):
        path = '/api/devType/{}'.format(pk)
        return self.client.adapter.delete(path)

    def create_dev(self, name, sys_type_name, department_id, ip='1', services=None):
        path = '/api/dev'
        type_id = self.DEV_TYPE_MAP[sys_type_name]['type']
        sys_type_id = self.read_dev_type_id(sys_type_name)

        data = {
            'name': name,
            'ip': ip,
            'type': type_id,
            'sysType': {'id': sys_type_id},
            'department': {'id': department_id},
            'networkEnvironment': {'id': 1},
            "charset": "UTF-8"
        }

        if services:
            data.pop('charset')
            data.update(services)

        return self.client.adapter.post(path, json=data)

    def read_dev(self, name, type_name, department_id, ip):
        path = '/api/dev'
        data = {
            'nameContains': name,
            'ipContains': ip,
            'sysType.nameIs': type_name,
            'department.idIs': department_id,
            'deletedIs': False
        }
        return self.client.adapter.get(path, params=data)['content']

    def delete_dev(self, pk):
        path = '/api/dev/{}'.format(pk)
        return self.client.adapter.delete(path)
