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
  description: MongoDB server version.
  returned: always
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
    mongo_auth,
    get_mongodb_client,
)


class MongoDBPing(object):
    def __init__(self, module, client):
        self.module = module
        self.client = client
        self.is_available = False
        self.conn_err_msg = ''
        self.version = ''

    def do(self):
        self.get_mongodb_version()
        return self.is_available, self.version

    def get_err(self):
        return self.conn_err_msg

    def get_mongodb_version(self):
        try:
            server_info = self.client.server_info()
            self.is_available = True
            self.version = server_info.get('version', '')
        except PyMongoError as err:
            self.is_available = False
            self.version = ''
            self.conn_err_msg = err


# =========================================
# Module execution.
#


def main():
    argument_spec = mongodb_common_argument_spec()
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = None
    result = {
        'changed': False, 'is_available': False, 'server_version': ''
    }
    try:
        client = get_mongodb_client(module, directConnection=True)
        client = mongo_auth(module, client, directConnection=True)
    except Exception as e:
        module.fail_json(msg='Unable to connect to database: %s' % to_native(e))

    mongodb_ping = MongoDBPing(module, client)
    result["is_available"], result["server_version"] = mongodb_ping.do()
    conn_err_msg = mongodb_ping.get_err()
    if conn_err_msg:
        module.fail_json(msg='Unable to connect to database: %s' % conn_err_msg)

    try:
        client.close()
    except Exception:
        pass

    return module.exit_json(**result)


if __name__ == '__main__':
    main()
