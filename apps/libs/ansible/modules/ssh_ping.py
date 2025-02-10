#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: ssh_ping
short_description: Use ssh to probe whether an asset is connectable
description:
    - Use ssh to probe whether an asset is connectable.
options:
    login_host:
        description: The target host to connect.
        type: str
        required: True
    login_port:
        description: The port on the target host.
        type: int
        required: False
        default: 22
    login_user:
        description: The username for the SSH connection.
        type: str
        required: True
    login_password:
        description: The password for the SSH connection.
        type: str
        required: True
        no_log: True
'''

EXAMPLES = '''
- name: Ping asset server using SSH.
  ssh_ping:
    login_host: 127.0.0.1
    login_port: 22
    login_user: jms
    login_password: password
'''

RETURN = '''
is_available:
  description: Indicate whether the target server is reachable via SSH.
  returned: always
  type: bool
  sample: true
'''

from ansible.module_utils.basic import AnsibleModule
from libs.ansible.modules_utils.remote_client import SSHClient, common_argument_spec


def main():
    options = common_argument_spec()
    module = AnsibleModule(argument_spec=options, supports_check_mode=True)

    result = {'changed': False, 'is_available': False}

    with SSHClient(module) as client:
        client.connect()

    result['is_available'] = True
    module.exit_json(**result)


if __name__ == '__main__':
    main()
