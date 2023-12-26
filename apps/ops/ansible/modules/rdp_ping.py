#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: custom_rdp_ping
short_description: Use rdp to probe whether an asset is connectable
description:
    - Use rdp to probe whether an asset is connectable
'''

EXAMPLES = '''
- name: >
    Ping asset server.
  custom_rdp_ping:
    login_host: 127.0.0.1
    login_port: 3389
    login_user: jms
    login_password: password
'''

RETURN = '''
is_available:
  description: Windows server availability.
  returned: always
  type: bool
  sample: true
conn_err_msg:
  description: Connection error message.
  returned: always
  type: str
  sample: ''
'''
import re
import pyfreerdp
from sshtunnel import SSHTunnelForwarder
from typing import NamedTuple
from ansible.module_utils.basic import AnsibleModule


# =========================================
# Module execution.
#

class Param(NamedTuple):
    hostname: str
    port: int
    username: str
    password: str


def common_argument_spec():
    options = dict(
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=3389),
        login_user=dict(type='str', required=False, default='administrator'),
        login_password=dict(type='str', required=False, no_log=True),
        login_secret_type=dict(type='str', required=False, default='password'),
        login_private_key_path=dict(type='str', required=False, no_log=True),
        gateway_args=dict(type='str', required=False, default=''),
    )
    return options


def local_gateway_prepare(params, gateway_args):
    gateway_args = gateway_args or ''
    if not gateway_args:
        return params, None

    pattern = r"(?:sshpass -p ([\w@]+))?\s*ssh -o Port=(\d+)\s+-o StrictHostKeyChecking=no\s+([\w@]+)@([" \
              r"\d.]+)\s+-W %h:%p -q(?: -i (.+))?'"
    match = re.search(pattern, gateway_args)

    if not match:
        return params, None

    password, port, username, address, private_key_path = match.groups()
    password = password if password else None
    private_key_path = private_key_path if private_key_path else None
    with open('/Users/xiaofeng/Desktop/jumpserver/apps/feng1.txt', 'w') as f:
        f.write(password + '\n')
        f.write(port + '\n')
        f.write(username + '\n')
        f.write(address)
    server = SSHTunnelForwarder(
        (address, int(port)),
        ssh_username=username,
        ssh_password=password,
        ssh_pkey=private_key_path,
        remote_bind_address=(address, params.port),
    )

    server.start()
    params.hostname = '127.0.0.1'
    params.port = server.local_bind_port
    return params, server


def local_gateway_clean(server):
    if not server:
        return
    try:
        server.stop()
    except Exception:
        pass


def run(module):
    params = Param(
        hostname=module.params['login_host'],
        port=module.params['login_port'],
        username=module.params['login_user'],
        password=module.params['login_password']
    )
    with open('/Users/xiaofeng/Desktop/jumpserver/apps/feng.txt', 'w') as f:
        f.write(str(params))
    gateway_args = module.params.get('gateway_args')
    params, server = local_gateway_prepare(params, gateway_args)
    is_available = pyfreerdp.check_connectivity(*params, '', 0)
    local_gateway_clean(server)
    return is_available


def main():
    options = common_argument_spec()
    module = AnsibleModule(argument_spec=options, supports_check_mode=True)
    result = {'changed': False, 'is_available': False}

    secret_type = module.params['login_secret_type']
    if secret_type != 'password':
        module.fail_json(
            msg=f'The current ansible does not support \
                the verification method for {secret_type} types.'
        )
        return module.exit_json(**result)

    is_available = run(module)
    result['is_available'] = is_available
    if not is_available:
        module.fail_json(msg='Unable to connect to asset.')
    return module.exit_json(**result)


if __name__ == '__main__':
    main()
