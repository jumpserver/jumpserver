#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: oracle_ping
short_description: Check remote Oracle server availability
description:
- Simple module to check remote Oracle server availability.

requirements:
  - "oracledb"
'''

EXAMPLES = '''
- name: >
    Ping Oracle server using non-default credentials and SSL
    registering the return values into the result variable for future use
  oracle_ping:
    login_host: jumpserver
    login_port: 1521
    login_user: jms
    login_password: secret_pass
    login_database: test_db
'''

RETURN = '''
is_available:
  description: Oracle server availability.
  returned: always
  type: bool
  sample: true
server_version:
  description: Oracle server version.
  returned: always
  type: str
  sample: '4.0.0'
conn_err_msg:
  description: Connection error message.
  returned: always
  type: str
  sample: ''
'''

from ansible.module_utils.basic import AnsibleModule
from ops.ansible.modules_utils.oracle_common import (
    OracleClient, oracle_common_argument_spec
)


class OracleDBPing(object):
    def __init__(self, module, oracle_client):
        self.module = module
        self.oracle_client = oracle_client
        self.is_available = False
        self.conn_err_msg = ''
        self.version = ''

    def do(self):
        self.get_oracle_version()
        return self.is_available, self.version

    def get_err(self):
        return self.conn_err_msg

    def get_oracle_version(self):
        version_sql = 'SELECT VERSION FROM PRODUCT_COMPONENT_VERSION where ROWNUM=1'
        rtn, err = self.oracle_client.execute(version_sql)
        if err:
            self.conn_err_msg = err
        else:
            self.version = rtn.get('version')
            self.is_available = True


# =========================================
# Module execution.
#


def main():
    argument_spec = oracle_common_argument_spec()
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    result = {
        'changed': False, 'is_available': False, 'server_version': ''
    }
    oracle_client = OracleClient(module)

    oracle_ping = OracleDBPing(module, oracle_client)
    result["is_available"], result["server_version"] = oracle_ping.do()
    conn_err_msg = oracle_ping.get_err()
    oracle_client.close()
    if conn_err_msg:
        module.fail_json(msg='Unable to connect to database: %s' % conn_err_msg)

    return module.exit_json(**result)


if __name__ == '__main__':
    main()
