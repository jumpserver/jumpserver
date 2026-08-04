#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: mongodb_ping
short_description: Check remote MongoDB server availability
description:
- Simple module to check remote MongoDB server availability.

requirements:
  - "pymongo"
'''

EXAMPLES = '''
- name: >
    Ping MongoDB server using non-default credentials and SSL
    registering the return values into the result variable for future use
  mongodb_ping:
    login_db: test_db
    login_host: jumpserver
    login_user: jms
    login_password: secret_pass
    ssl: True
    ssl_ca_certs: "/tmp/ca.crt"
    ssl_certfile: "/tmp/tls.key" #cert and key in one file
    connection_options:
     - "tlsAllowInvalidHostnames=true"
'''

RETURN = '''
is_available:
  description: MongoDB server availability.
  returned: always
  type: bool
  sample: true
server_version:
  description: MongoDB server version when gather_version is enabled.
  returned: when gather_version is enabled
  type: str
  sample: '4.0.0'
conn_err_msg:
  description: Connection error message.
  returned: always
  type: str
  sample: ''
'''


from pymongo.errors import PyMongoError
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import (
    mongodb_common_argument_spec,
)
from libs.ansible.modules_utils.mongodb_client import (
    get_authenticated_mongodb_client,
)


class MongoDBPing(object):
    def __init__(self, module, client):
        self.module = module
        self.client = client
        self.is_available = False
        self.conn_err_msg = ''
        self.version = ''
        self.users = {}

    def do(self):
        self.probe()
        return self.is_available, self.version, self.users

    def get_err(self):
        return self.conn_err_msg

    def probe(self):
        try:
            self.client.admin.command('ping')
            self.is_available = True
            if self.module.params['gather_version']:
                server_info = self.client.server_info()
                self.version = server_info.get('version', '')
            if self.module.params['gather_users']:
                self.users = self.get_users()
        except PyMongoError as err:
            self.is_available = False
            self.version = ''
            self.users = {}
            self.conn_err_msg = err

    def get_users(self):
        result = {}
        for database_name in self.client.list_database_names():
            users = self.client[database_name].command(
                {'usersInfo': 1}
            ).get('users', [])
            result[database_name] = {
                user['user']: {
                    'roles': user.get('roles', []),
                }
                for user in users
                if user.get('user')
            }
        return result


# =========================================
# Module execution.
#


def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        gather_version=dict(type='bool', default=False),
        gather_users=dict(type='bool', default=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = None
    result = {
        'changed': False,
        'is_available': False,
        'server_version': '',
        'users': {},
    }
    try:
        client = get_authenticated_mongodb_client(module)
    except Exception as e:
        module.fail_json(msg='Unable to connect to database: %s' % to_native(e))

    mongodb_ping = MongoDBPing(module, client)
    (
        result["is_available"],
        result["server_version"],
        result["users"],
    ) = mongodb_ping.do()
    conn_err_msg = mongodb_ping.get_err()
    if conn_err_msg:
        module.fail_json(msg='Unable to connect to database: %s' % conn_err_msg)

    try:
        client.close()
    except Exception: # noqa
        pass

    return module.exit_json(**result)


if __name__ == '__main__':
    main()
