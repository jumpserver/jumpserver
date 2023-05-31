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

import pyfreerdp
from typing import NamedTuple
from ansible.module_utils.basic import AnsibleModule

from ops.ansible.modules_utils.custom_common import (
    common_argument_spec
)


# =========================================
# Module execution.
#

class Param(NamedTuple):
    hostname: str
    port: int
    username: str
    password: str


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

    params = Param(
        hostname=module.params['login_host'],
        port=module.params['login_port'],
        username=module.params['login_user'],
        password=module.params['login_password']
    )

    is_available = pyfreerdp.check_connectivity(*params, '', 0)
    result['is_available'] = is_available
    if not is_available:
        module.fail_json(msg='Unable to connect to asset.')
    return module.exit_json(**result)


if __name__ == '__main__':
    main()
