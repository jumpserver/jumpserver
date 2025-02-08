#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = '''
---
module: ssh_ping
short_description: Use ssh to probe whether an asset is connectable
description:
    - Use ssh to probe whether an asset is connectable
'''

EXAMPLES = '''
- name: >
    Ping asset server.
  ssh_ping:
    login_host: 127.0.0.1
    login_port: 22
    login_user: jms
    login_password: password
'''

RETURN = '''
is_available:
  description: Ping server availability.
  returned: always
  type: bool
  sample: true
'''


from ansible.module_utils.basic import AnsibleModule

from libs.ansible.modules_utils.remote_client import (
    SSHClient, common_argument_spec
)


# =========================================
# Module execution.
#


def main():
    options = common_argument_spec()
    module = AnsibleModule(argument_spec=options, supports_check_mode=True,)

    result = {
        'changed': False, 'is_available': False
    }
    with SSHClient(module) as client:
        client.connect()
    result['is_available'] = True
    return module.exit_json(**result)


if __name__ == '__main__':
    main()
