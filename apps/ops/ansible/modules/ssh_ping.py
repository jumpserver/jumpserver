#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = '''
---
module: custom_ssh_ping
short_description: Use ssh to probe whether an asset is connectable
description:
    - Use ssh to probe whether an asset is connectable
'''

EXAMPLES = '''
- name: >
    Ping asset server.
  custom_ssh_ping:
    login_host: 127.0.0.1
    login_port: 22
    login_user: jms
    login_password: password
'''

RETURN = '''
is_available:
  description: MongoDB server availability.
  returned: always
  type: bool
  sample: true
conn_err_msg:
  description: Connection error message.
  returned: always
  type: str
  sample: ''
'''


from ansible.module_utils.basic import AnsibleModule

from ops.ansible.modules_utils.custom_common import (
    SSHClient, common_argument_spec
)


# =========================================
# Module execution.
#


def main():
    options = common_argument_spec()
    module = AnsibleModule(argument_spec=options, supports_check_mode=True,)

    result = {
        'changed': False, 'is_available': True
    }
    client = SSHClient(module)
    err = client.connect()
    if err:
        module.fail_json(msg='Unable to connect to asset: %s' % err)
        result['is_available'] = False

    return module.exit_json(**result)


if __name__ == '__main__':
    main()
